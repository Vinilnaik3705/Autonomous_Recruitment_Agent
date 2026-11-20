"""Recruitment application and workflow endpoints."""

import hashlib
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from psycopg.types.json import Jsonb
from pydantic import AwareDatetime, EmailStr

from backend.api.auth_router import router
from backend.config import get_settings
from backend.database import make_pool
from backend.db.queries import (
    applications,
    interviews,
    jobs,
    onboarding,
    resumes,
    runs,
    users,
)
from backend.embeddings.provider import LocalMiniLM
from backend.orchestration.status import CandidateStatus, validate_transition
from backend.schemas.recruitment import (
    ApplicationReceipt,
    InterviewFeedback,
    JobInput,
    Reconciliation,
    StageChange,
)
from backend.security.dependencies import Connection, Staff, User
from backend.services.google_workspace import availability, reschedule_conflict
from backend.workers.pipeline import record_delivery


@asynccontextmanager
async def lifespan(app):
    with make_pool() as pool:
        pool.wait(timeout=10)
        app.state.db_pool = pool
        yield


app = FastAPI(title="Autonomous Recruitment Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router)


@app.get("/health")
def health(conn: Connection):
    conn.execute("SELECT 1")
    return {"status": "ready"}


@app.post("/jobs", status_code=201)
def create_job(body: JobInput, conn: Connection, user: Staff):
    return jobs.create(conn, body, user["id"], LocalMiniLM().encode(body.description))


@app.get("/jobs")
def open_jobs(conn: Connection, _user: User):
    return jobs.list_open(conn)


@app.get("/jobs/{job_id}/matches")
def matching(job_id: int, conn: Connection, _user: Staff, limit: int = 10):
    if not 1 <= limit <= 100:
        raise HTTPException(422, "Limit must be between 1 and 100")
    job = jobs.embedding_for(conn, job_id)
    if not job or job["embedding"] is None:
        raise HTTPException(404, "Job embedding unavailable")
    return applications.similar(conn, job_id, job["embedding"], limit)


@app.post("/applications", status_code=202, response_model=ApplicationReceipt)
def submit(
    conn: Connection,
    user: User,
    file: UploadFile,
    job_id: int = Form(),
    full_name: str = Form(min_length=1, max_length=200),
    email: EmailStr | None = Form(None),
):
    if user["role"] not in {"candidate", "hr", "admin"}:
        raise HTTPException(403, "Candidate or HR access required")
    candidate_id = user["id"] if user["role"] == "candidate" else None
    address = user["email"] if candidate_id else str(email or "").lower()
    if not address:
        raise HTTPException(422, "Candidate email required")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(415, "Upload a PDF or DOCX")
    data = file.file.read(8 * 1024 * 1024 + 1)
    if not data or len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "Upload a nonempty file of at most 8 MiB")
    resume_path = resumes.store(conn, data, suffix)
    row = applications.create(
        conn, job_id, full_name.strip(), address, candidate_id, resume_path
    )
    if not row:
        raise HTTPException(409, "Job is closed or this candidate already applied")
    runs.enqueue(conn, row["id"], "screen", f"screen:{row['id']}")
    if candidate_id is None:
        code = secrets.token_urlsafe(32)
        runs.enqueue(
            conn,
            row["id"],
            "invite",
            f"invite:{row['id']}",
            {
                "claim_hash": hashlib.sha256(code.encode()).hexdigest(),
                "subject": "Track your application",
                "text": f"Application ID: {row['id']}\nInvitation code: {code}",
            },
        )
    return row


@app.get("/applications")
def list_applications(conn: Connection, user: User):
    if user["role"] == "interviewer":
        raise HTTPException(403, "Use the assigned interview workflow")
    return applications.list_for(
        conn, user["id"] if user["role"] == "candidate" else None
    )


@app.post("/applications/{application_id}/claim")
def claim(
    application_id: int,
    conn: Connection,
    user: User,
    code: str = Form(min_length=32, max_length=100),
):
    if not applications.claim(
        conn, application_id, user, hashlib.sha256(code.encode()).hexdigest()
    ):
        raise HTTPException(404, "Invalid invitation")
    return {"status": "linked"}


@app.post("/applications/{application_id}/retry")
def retry(application_id: int, conn: Connection, _user: Staff):
    if not runs.retry_screening(conn, application_id):
        raise HTTPException(409, "No failed screening to retry")
    return {"status": "queued"}


@app.get("/calendar/availability")
def calendar_availability(start: AwareDatetime, end: AwareDatetime, _user: Staff):
    if end <= start:
        raise HTTPException(422, "End must follow start")
    return availability(start, end)


@app.post("/applications/{application_id}/stage")
def change_stage(application_id: int, body: StageChange, conn: Connection, user: Staff):
    application = applications.lock(conn, application_id)
    if not application:
        raise HTTPException(404, "Application not found")
    current, target = CandidateStatus(application["status"]), body.target
    if runs.pending_for(conn, application_id):
        raise HTTPException(409, "Resolve the pending scheduling or offer action first")
    reschedule = current == target == CandidateStatus.INTERVIEW_SCHEDULED
    if not reschedule:
        try:
            validate_transition(current, target, hr_approved=True)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
    if target == CandidateStatus.SCREENED:
        raise HTTPException(409, "Only the screening worker can complete screening")
    if target == CandidateStatus.INTERVIEW_SCHEDULED:
        start = body.scheduled_start
        interviewer = (
            users.by_id(conn, body.interviewer_id) if body.interviewer_id else None
        )
        if not start or start <= datetime.now(timezone.utc):
            raise HTTPException(422, "A future interview time is required")
        if (
            not interviewer
            or not interviewer["is_active"]
            or interviewer["role"] != "interviewer"
        ):
            raise HTTPException(422, "Choose an active interviewer")
        end = start + timedelta(hours=1)
        if interviews.reserve_calendar(conn, application_id, start, end):
            raise HTTPException(409, "That calendar slot is reserved")
        busy = (
            reschedule_conflict(application_id, start, end)
            if reschedule
            else availability(start, end)
        )
        if busy:
            raise HTTPException(409, "That calendar slot is busy")
        action = "reschedule" if reschedule else "book"
        queued = runs.enqueue(
            conn,
            application_id,
            action,
            f"{action}:{application_id}:{start.astimezone(timezone.utc).isoformat()}",
            {
                "start": start.isoformat(),
                "interviewer_id": interviewer["id"],
                "expected_status": current.value,
            },
        )
        if not queued:
            raise HTTPException(409, "This calendar request was already recorded")
        return {"status": "queued"}
    if target == CandidateStatus.FEEDBACK_RECEIVED:
        if not interviews.feedback(
            conn,
            application_id,
            body.feedback_comments,
            Jsonb(body.feedback_scores or {}),
            body.recommendation,
        ):
            raise HTTPException(
                409, "Feedback is already submitted or no interview exists"
            )
    if target == CandidateStatus.OFFER_SENT:
        if not body.offer_text:
            raise HTTPException(422, "Offer text is required")
        applications.approve_offer(conn, application_id, user["id"])
        runs.enqueue(
            conn,
            application_id,
            "offer",
            f"offer:{application_id}",
            {
                "subject": "Offer",
                "text": body.offer_text,
                "expected_status": current.value,
            },
        )
        return {"status": "queued"}
    if target == CandidateStatus.ONBOARDING:
        if not body.checklist or not all(item.strip() for item in body.checklist):
            raise HTTPException(422, "An onboarding checklist is required")
        for item in body.checklist:
            onboarding.create(conn, application_id, item.strip(), body.due_date)
    if target == CandidateStatus.COMPLETE and any(
        task["status"] != "verified"
        for task in onboarding.list_for(conn, application_id)
    ):
        raise HTTPException(409, "Verify all onboarding tasks first")
    approver = user["id"] if target == CandidateStatus.REJECTED else None
    applications.set_status(conn, application_id, target.value, approver)
    runs.record_transition(conn, application_id, current.value, target.value)
    return {"status": target}


def task_access(conn, application_id, user):
    if user["role"] in {"admin", "hr"}:
        return
    if user["role"] != "candidate" or not applications.owned_by(
        conn, application_id, user["id"]
    ):
        raise HTTPException(404, "Application not found")


@app.get("/applications/{application_id}/onboarding")
def tasks(application_id: int, conn: Connection, user: User):
    task_access(conn, application_id, user)
    return onboarding.list_for(conn, application_id)


@app.post("/applications/{application_id}/onboarding/{task_id}")
def advance_task(application_id: int, task_id: int, conn: Connection, user: User):
    task_access(conn, application_id, user)
    before, after = (
        ("pending", "submitted")
        if user["role"] == "candidate"
        else ("submitted", "verified")
    )
    if not onboarding.update(conn, application_id, task_id, before, after):
        raise HTTPException(409, "Task is not ready for this action")
    return {"status": after}


@app.post("/actions/{action_id}/reconcile")
def reconcile(action_id: int, body: Reconciliation, conn: Connection, _user: Staff):
    run = runs.lock(conn, action_id)
    if not run or run["details"].get("delivery") != "uncertain":
        raise HTTPException(409, "Action does not require reconciliation")
    if body.delivered:
        if not body.provider_id:
            raise HTTPException(422, "Provider receipt is required")
        record_delivery(conn, run, body.provider_id)
        runs.update(conn, action_id, "success", "sent", reconciliation_note=body.note)
    else:
        runs.update(conn, action_id, "running", "queued", reconciliation_note=body.note)
    return {"status": "reconciled"}


@app.get("/interviewers")
def list_interviewers(conn: Connection, _user: Staff):
    return users.interviewers(conn)


@app.get("/interviews/assigned")
def assigned_interviews(conn: Connection, user: User):
    if user["role"] != "interviewer":
        raise HTTPException(403, "Interviewer access required")
    return interviews.assigned(conn, user["id"])


@app.post("/interviews/{application_id}/feedback")
def interviewer_feedback(
    application_id: int, body: InterviewFeedback, conn: Connection, user: User
):
    application = applications.lock(conn, application_id)
    interview = interviews.get(conn, application_id)
    if (
        not application
        or not interview
        or user["role"] != "interviewer"
        or interview["interviewer_id"] != user["id"]
    ):
        raise HTTPException(404, "Interview not found")
    if application["status"] != "interviewed":
        raise HTTPException(409, "HR must first mark the interview complete")
    if not interviews.feedback(
        conn, application_id, body.comments, Jsonb(body.scores), body.recommendation
    ):
        raise HTTPException(409, "Feedback already submitted")
    applications.set_status(conn, application_id, "feedback_received")
    runs.record_transition(conn, application_id, "interviewed", "feedback_received")
    return {"status": "feedback_received"}


@app.get("/applications/{application_id}/activity")
def application_activity(application_id: int, conn: Connection, _user: Staff):
    return runs.activity(conn, application_id)

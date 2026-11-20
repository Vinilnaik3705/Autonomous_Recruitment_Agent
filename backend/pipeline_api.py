"""Single-team recruitment API. Run migrations before starting this service."""

import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extras import Json
from pydantic import AwareDatetime, BaseModel, EmailStr, Field

from backend.api.auth_router import router as auth_router
from backend.config import get_settings
from backend.orchestration.status import CandidateStatus, validate_transition
from backend.security.dependencies import get_current_user, require_role
from backend.services.google_workspace import availability, reschedule_conflict
from backend.workers.pipeline import record_delivery, transaction

app = FastAPI(title="Autonomous Recruitment Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
if supabase_url:
    from backend.api.auth_router import get_current_user_info
    if not os.getenv("SUPABASE_PUBLISHABLE_KEY", "").startswith("sb_publishable_"):
        raise RuntimeError("Set a Supabase publishable key for hosted authentication")
    app.get("/auth/me")(get_current_user_info)
else:
    app.include_router(auth_router)


@app.get("/auth/config")
def auth_config():
    if supabase_url:
        return {"provider":"supabase","url":supabase_url,"key":os.environ["SUPABASE_PUBLISHABLE_KEY"]}
    return {"provider":"local"}

Staff = Annotated[dict, Depends(require_role("recruiter", "hr"))]
User = Annotated[dict, Depends(get_current_user)]


@app.get("/health")
def health():
    with transaction() as cur:
        cur.execute("SELECT 1 FROM agent_runs LIMIT 1")
    return {"status": "ready"}


@app.post("/runs", status_code=202)
async def submit(
    user: Staff,
    file: UploadFile,
    email: Annotated[EmailStr, Form()],
    job_description: Annotated[str, Form(min_length=1, max_length=20000)],
    request_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    required_skills: Annotated[str, Form(max_length=4000)] = "",
):
    name = file.filename or ""
    if not name.lower().endswith((".pdf", ".docx")):
        raise HTTPException(415, "Upload a PDF or DOCX")
    data = await file.read(8 * 1024 * 1024 + 1)
    if not data or len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "Upload a nonempty file of at most 8 MiB")
    code = secrets.token_urlsafe(32)
    with transaction() as cur:
        cur.execute(
            """INSERT INTO agent_runs(owner_id,request_key,email,filename,document,job_description,required_skills,claim_hash)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(owner_id,request_key) DO NOTHING RETURNING id""",
            (
                user["user_id"],
                str(request_key),
                email,
                name,
                data,
                job_description,
                [s.strip() for s in required_skills.split(",") if s.strip()],
                hashlib.sha256(code.encode()).hexdigest(),
            ),
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                "INSERT INTO recruitment_actions(run_id,kind,body) VALUES (%s,'invitation',%s)",
                (
                    row["id"],
                    Json(
                        {
                            "subject": "Track your application",
                            "text": f"Sign in to the candidate portal with this email and enter your invitation code: {code}",
                        }
                    ),
                ),
            )
        else:
            cur.execute(
                "SELECT id FROM agent_runs WHERE owner_id=%s AND request_key=%s",
                (user["user_id"], str(request_key)),
            )
            row = cur.fetchone()
        return row


@app.get("/runs")
def list_runs(user: Staff):
    with transaction() as cur:
        cur.execute(
            """SELECT r.id,email,filename,stage,screening_state,result,interview_at,feedback,checklist,
                       (SELECT json_agg(json_build_object('id',id,'kind',kind,'state',state) ORDER BY id)
                        FROM recruitment_actions WHERE run_id=r.id) AS actions
                       FROM agent_runs r ORDER BY id DESC LIMIT 100"""
        )
        return cur.fetchall()


@app.post("/runs/{run_id}/retry")
def retry(run_id: int, user: Staff):
    with transaction() as cur:
        cur.execute(
            "UPDATE agent_runs SET screening_state='queued' WHERE id=%s AND screening_state='failed' RETURNING id",
            (run_id,),
        )
        if not cur.fetchone():
            raise HTTPException(409, "Only failed screening runs can be retried")
    return {"status": "queued"}


@app.get("/calendar/availability")
def check_availability(start: AwareDatetime, user: Staff):
    return {"busy": availability(start, start + timedelta(hours=1))}


class Change(BaseModel):
    target: CandidateStatus
    start: AwareDatetime | None = None
    note: str = Field(default="", max_length=20000)
    checklist: list[str] = Field(default_factory=list, max_length=50)


@app.post("/runs/{run_id}/stage")
def change_stage(run_id: int, change: Change, user: Staff):
    target = change.target
    with transaction() as cur:
        cur.execute(
            "SELECT stage,interview_at FROM agent_runs WHERE id=%s FOR UPDATE",
            (run_id,),
        )
        run = cur.fetchone()
        if not run:
            raise HTTPException(404, "Unknown run")
        current = CandidateStatus(run["stage"])
        cur.execute(
            """SELECT 1 FROM recruitment_actions WHERE run_id=%s AND kind IN ('book','reschedule','offer')
                       AND state IN ('pending','sending','uncertain')""",
            (run_id,),
        )
        if cur.fetchone():
            raise HTTPException(
                409, "Resolve the outstanding delivery before changing the stage"
            )
        rescheduling = current == target == CandidateStatus.INTERVIEW_SCHEDULED
        if not rescheduling:
            try:
                validate_transition(current, target, hr_approved=user["role"] == "hr")
            except ValueError as exc:
                raise HTTPException(409, str(exc))
            except PermissionError as exc:
                raise HTTPException(403, str(exc))
        if target == CandidateStatus.SCREENED:
            raise HTTPException(409, "Screening is performed by the worker")
        if (
            target in (CandidateStatus.FEEDBACK_RECEIVED, CandidateStatus.OFFER_SENT)
            and not change.note.strip()
        ):
            raise HTTPException(422, "Supply written feedback or offer terms")
        if target == CandidateStatus.INTERVIEW_SCHEDULED:
            if not change.start or change.start <= datetime.now(timezone.utc):
                raise HTTPException(422, "Select a future interview time")
            if rescheduling and run["interview_at"] == change.start:
                return {"status": current}
            # Serialize overlapping booking requests on the team's single calendar.
            cur.execute("SELECT pg_advisory_xact_lock(781291)")
            end = change.start + timedelta(hours=1)
            cur.execute(
                """SELECT 1 FROM recruitment_actions WHERE kind IN ('book','reschedule')
                AND state IN ('pending','sending','uncertain')
                AND (body->>'start')::timestamptz < %s
                AND (body->>'start')::timestamptz + interval '1 hour' > %s LIMIT 1""",
                (end, change.start),
            )
            if cur.fetchone():
                raise HTTPException(409, "Another booking is pending for this slot")
            busy = (
                reschedule_conflict(run_id, change.start, end)
                if rescheduling
                else availability(change.start, end)
            )
            if busy:
                raise HTTPException(409, "The calendar slot is busy")
            kind = "reschedule" if rescheduling else "book"
            body = {"start": change.start.isoformat()}
        elif target == CandidateStatus.OFFER_SENT:
            cur.execute(
                "UPDATE agent_runs SET approved_by=%s, offer=%s WHERE id=%s",
                (user["user_id"], change.note, run_id),
            )
            kind, body = "offer", {
                "subject": "Offer of employment",
                "text": change.note,
            }
        else:
            if target == CandidateStatus.ONBOARDING and not all(
                s.strip() for s in change.checklist
            ):
                raise HTTPException(422, "Each checklist item needs a name")
            if target == CandidateStatus.ONBOARDING and not change.checklist:
                raise HTTPException(422, "Provide the onboarding checklist")
            if target == CandidateStatus.COMPLETE and not change.note.strip():
                raise HTTPException(422, "Record how the checklist was verified")
            cur.execute(
                """UPDATE agent_runs SET stage=%s,
                        feedback=CASE WHEN %s='feedback_received' THEN %s ELSE feedback END,
                        checklist=CASE WHEN %s='onboarding' THEN %s ELSE checklist END,
                        completion_note=CASE WHEN %s='complete' THEN %s ELSE completion_note END,
                        approved_by=CASE WHEN %s='rejected' THEN %s ELSE approved_by END WHERE id=%s""",
                (
                    target.value,
                    target.value,
                    change.note,
                    target.value,
                    change.checklist,
                    target.value,
                    change.note,
                    target.value,
                    user["user_id"],
                    run_id,
                ),
            )
            if target != CandidateStatus.ONBOARDING:
                return {"status": target}
            kind, body = "onboarding", {
                "subject": "Your onboarding checklist",
                "text": "\n".join(change.checklist),
            }
        cur.execute(
            "INSERT INTO recruitment_actions(run_id,kind,body) VALUES (%s,%s,%s)",
            (run_id, kind, Json(body)),
        )
    return {"status": "queued" if kind != "onboarding" else "onboarding"}


@app.get("/applications")
def applications(user: User):
    with transaction() as cur:
        cur.execute(
            """SELECT id,stage,interview_at,checklist FROM agent_runs
                       WHERE candidate_user_id=%s ORDER BY id DESC""",
            (user["user_id"],),
        )
        return cur.fetchall()


@app.post("/applications/claim")
def claim(user: User, code: str = Form(min_length=32, max_length=100)):
    with transaction() as cur:
        cur.execute(
            """UPDATE agent_runs SET candidate_user_id=%s, claim_hash=NULL
                       WHERE claim_hash=%s AND lower(email)=lower(%s) RETURNING id""",
            (user["user_id"], hashlib.sha256(code.encode()).hexdigest(), user["email"]),
        )
        if not cur.fetchone():
            raise HTTPException(404, "Invalid invitation")
    return {"status": "linked"}


class Reconciliation(BaseModel):
    delivered: bool
    evidence: str = Field(min_length=8, max_length=1000)
    provider_id: str | None = Field(default=None, max_length=500)


@app.post("/actions/{action_id}/reconcile")
def reconcile(
    action_id: int,
    decision: Reconciliation,
    user: Annotated[dict, Depends(require_role("hr"))],
):
    """HR checks the remote mailbox/calendar after an ambiguous network outcome."""
    with transaction() as cur:
        cur.execute(
            "SELECT * FROM recruitment_actions WHERE id=%s FOR UPDATE", (action_id,)
        )
        action = cur.fetchone()
        if not action or action["state"] != "uncertain":
            raise HTTPException(409, "Only uncertain deliveries can be reconciled")
        if decision.delivered:
            if not decision.provider_id or not decision.provider_id.strip():
                raise HTTPException(
                    422, "Enter the message or event ID from the provider"
                )
            record_delivery(cur, action, decision.provider_id)
        else:
            cur.execute(
                "UPDATE recruitment_actions SET state='pending',claimed_at=NULL WHERE id=%s",
                (action_id,),
            )
        cur.execute(
            "UPDATE recruitment_actions SET reconciled_by=%s,reconciliation_note=%s WHERE id=%s",
            (user["user_id"], decision.evidence, action_id),
        )
    return {"status": "sent" if decision.delivered else "pending"}

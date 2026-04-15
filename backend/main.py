import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Dict, Optional, List
import requests
from backend.services.resume_service import parse_resume, save_resume_to_db, save_resumes_batch
from backend.database import get_db_connection
from backend.phase_logger import log_phase_completion
from backend.routers import email_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="HR Automation Agent API")  # v3: force reload

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(email_router.router)
from backend.routers import job_router, auth_router, candidate_router, notification_router, oa_router
app.include_router(job_router.router)
app.include_router(auth_router.router)
app.include_router(candidate_router.router)
app.include_router(notification_router.router)
app.include_router(oa_router.router)
app.include_router(oa_router.webhook_router)

@app.on_event("startup")
async def startup_event():
    # Keep local uvicorn runs aligned with docker startup behavior.
    from backend.init_db import init_db
    init_db()

    print("--> STARTUP: Listing all registered routes:")
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"   Route: {route.path}")
    print("------------------------------------------")
    
    global scheduler, feedback_service, onboarding_service, resume_agent, matcher_service
    
    # Import services here to avoid "app not loaded" or multiprocessing issues
    from backend.services.scheduling_service import SchedulingService
    from backend.services.feedback_service import FeedbackService
    from backend.services.onboarding_service import OnboardingService
    from backend.agents.resume_analyzer import ResumeAnalyzerAgent
    from backend.services.matching_service import get_matching_service

    print("--> STARTUP: Initializing services...")
    scheduler = SchedulingService()
    feedback_service = FeedbackService()
    onboarding_service = OnboardingService()
    resume_agent = ResumeAnalyzerAgent()
    # matcher_service = get_matching_service()  # Uses singleton to avoid double model loading
    print("--> STARTUP: Services initialized.")

# Services
# Services (initialized in startup_event)
scheduler = None
feedback_service = None
onboarding_service = None
resume_agent = None
matcher_service = None

def _repair_incomplete_scheduled_interviews():
    """
    Backfill scheduled interview rows that were inserted with placeholder
    candidate/email/time by external workflow SQL nodes.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Active interview rows ordered by creation.
            cur.execute(
                """
                SELECT id, interviewer_id, candidate_name, candidate_email, scheduled_time, created_at
                FROM interview_schedules
                WHERE status IN ('scheduled', 'in_progress')
                ORDER BY created_at ASC
                """
            )
            active_rows = cur.fetchall() or []
            if not active_rows:
                conn.rollback()
                return

            # Canonical shortlist source after screening - prioritize interview_status = 'shortlisted'
            cur.execute(
                """
                SELECT
                    COALESCE(NULLIF(TRIM(candidate_name), ''), 'Candidate') AS resolved_name,
                    LOWER(TRIM(email)) AS resolved_email
                FROM resume_data
                WHERE email IS NOT NULL
                  AND TRIM(email) <> ''
                  AND (
                    interview_status = 'shortlisted'
                    OR (interview_status ILIKE 'shortlist%' AND ai_score >= 35)
                    OR (interview_status IS NULL AND ai_score >= 60)
                  )
                ORDER BY
                  CASE
                    WHEN interview_status = 'shortlisted' THEN 0
                    WHEN interview_status ILIKE 'shortlist%' THEN 1
                    ELSE 2
                  END ASC,
                  ai_score DESC NULLS LAST,
                  created_at DESC
                """
            )
            shortlist = [
                (str(r[0]).strip(), str(r[1]).strip().lower())
                for r in (cur.fetchall() or [])
                if r and r[1]
            ]
            shortlist_emails = {email for _name, email in shortlist}

            # Track active rows already correctly bound to shortlist emails.
            bound_emails = set()
            repaired = 0
            now_utc = datetime.now(timezone.utc)

            for row in active_rows:
                row_id, _interviewer_id, raw_name, raw_email, raw_scheduled_time, _created_at = row
                email_norm = str(raw_email or "").strip().lower()
                name_norm = str(raw_name or "").strip()
                name_bad = (not name_norm) or name_norm.lower() in ("candidate", "unknown")
                time_bad = raw_scheduled_time is None
                if raw_scheduled_time is not None:
                    sched_dt = raw_scheduled_time if raw_scheduled_time.tzinfo else raw_scheduled_time.replace(tzinfo=timezone.utc)
                    if sched_dt <= now_utc + timedelta(minutes=30):
                        time_bad = True

                # Keep valid, uniquely mapped shortlist rows.
                if email_norm and email_norm in shortlist_emails and email_norm not in bound_emails and not name_bad and not time_bad:
                    bound_emails.add(email_norm)
                    continue

                # Assign next unbound shortlisted candidate.
                pick_name = None
                pick_email = None
                for s_name, s_email in shortlist:
                    if s_email not in bound_emails:
                        pick_name = s_name
                        pick_email = s_email
                        bound_emails.add(s_email)
                        break

                # If no shortlisted candidate remains, cancel placeholder duplicate rows.
                if not pick_email:
                    cur.execute(
                        """
                        UPDATE interview_schedules
                        SET status = 'cancelled',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (row_id,),
                    )
                    repaired += 1
                    continue

                # Deterministic next-day slot in UTC for repaired rows.
                next_day = (now_utc + timedelta(days=1)).date()
                hour_slot = 10 + (int(row_id) % 4)
                fixed_time = datetime(
                    next_day.year,
                    next_day.month,
                    next_day.day,
                    hour_slot,
                    0,
                    0,
                    tzinfo=timezone.utc,
                )
                if not time_bad and raw_scheduled_time is not None:
                    fixed_time = raw_scheduled_time

                cur.execute(
                    """
                    UPDATE interview_schedules
                    SET candidate_name = %s,
                        candidate_email = %s,
                        scheduled_time = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (pick_name or "Candidate", pick_email, fixed_time, row_id),
                )
                repaired += 1

        if repaired:
            conn.commit()
        else:
            conn.rollback()
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[repair] skipped incomplete interview repair: {e}")
    finally:
        if conn:
            conn.close()

def process_batch_files(files_data: List[Dict], user_id: int):
    """Background task to process files and save to DB."""
    try:
        # files_data is a list of {"filename": str, "content": bytes}
        parsed_data = []
        for f in files_data:
            try:
                data = parse_resume(f['content'], f['filename'])
                parsed_data.append(data)
            except Exception as e:
                print(f"Error parsing {f['filename']}: {e}")
        
        if parsed_data:
            save_resumes_batch(parsed_data, user_id)
            print(f"Values saved for batch of {len(parsed_data)} files")
            log_phase_completion(
                "Resume Screening",
                f"batch_processed={len(parsed_data)} user_id={user_id}",
            )
            
    except Exception as e:
        print(f"Batch processing failed: {e}")

# --- Phase 2: Resume Screening ---
@app.post("/resume/upload-batch")
async def upload_resume_batch(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...), user_id: int = 1):
    try:
        # Read files into memory (careful with large batches, but 50 files * 1MB = 50MB is fine)
        # If files are too large, we should save to disk first. Assuming controlled batch size from frontend.
        files_data = []
        for file in files:
            content = await file.read()
            files_data.append({"filename": file.filename, "content": content})
        
        background_tasks.add_task(process_batch_files, files_data, user_id)
        
        return {"status": "processing", "message": f"Received {len(files)} files for processing in background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resume/analyze")
async def analyze_resume(file: UploadFile = File(...), user_id: int = 1):
    try:
        content = await file.read()
        data = parse_resume(content, file.filename)
        file_id = save_resume_to_db(data, user_id)
        return {"status": "success", "file_id": file_id, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SentimentRequest(BaseModel):
    resume_text: Optional[str] = None

@app.post("/resume/sentiment")
async def resume_sentiment(file: Optional[UploadFile] = File(None), req_text: Optional[str] = None):
    """
    Analyze sentiment and summary of a resume.
    Accepts either:
    - file: multipart file upload
    - req_text: raw resume text in query parameter
    """
    try:
        resume_text = None
        filename = None
        
        if file:
            # File upload path
            content = await file.read()
            data = parse_resume(content, file.filename)
            resume_text = data['raw_text']
            filename = file.filename
        elif req_text:
            # Raw text path
            resume_text = req_text
            filename = "text_input"
        else:
            raise HTTPException(status_code=400, detail="Provide either file or req_text parameter")
        
        analysis = resume_agent.analyze_sentiment_and_summary(resume_text)
        return {"filename": filename, "analysis": analysis, "status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ResumeScoreRequest(BaseModel):
    resume_text: str
    job_description: str

@app.post("/resume/score-with-embeddings")
def score_resume_with_embeddings(req: ResumeScoreRequest):
    """
    Score a single resume using embeddings-based semantic similarity.
    Used by n8n workflow for individual resume processing.
    Uses proper parsing from resume_service for accurate name/email/skills extraction.
    """
    try:
        from backend.services.matching_service import get_matching_service
        from backend.services.resume_service import extract_name, extract_email, extract_contact_number, extract_skills
        
        # Use proper parsing functions for accurate extraction
        name = extract_name(req.resume_text) or "Unknown"
        email = extract_email(req.resume_text) or ""
        phone = extract_contact_number(req.resume_text) or ""
        skills = extract_skills(req.resume_text)
        
        # Use singleton MatchingService (avoids reloading the model each call)
        matching_service = get_matching_service()
        resume_data = [{
            'name': name,
            'email': email,
            'phone': phone,
            'resume_text': req.resume_text,
            'skills': skills
        }]
        
        scored_results = matching_service.score_new_resumes_for_job(
            job_description=req.job_description,
            resume_data_list=resume_data,
            threshold=35.0
        )
        
        # Always return a result, even if scoring partially fails
        if scored_results:
            result = scored_results[0]
            skills_str = ", ".join(result['skills']) if isinstance(result['skills'], list) else str(result['skills'])
            return {
                "candidate_name": result['candidate_name'],
                "email": result['email'],
                "phone": result['phone'],
                "skills": skills_str,
                "score": result['score'],
                "summary": f"Match score: {result['score']:.2f}/100 (Threshold: {result.get('threshold', 35)})",
                "shortlisted": result['shortlisted']
            }
        else:
            # Fallback: return with 0 score rather than failing
            skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
            return {
                "candidate_name": name,
                "email": email,
                "phone": phone,
                "skills": skills_str,
                "score": 0,
                "summary": "Scoring model unavailable",
                "shortlisted": False
            }
            
    except Exception as e:
        print(f"Error in score_resume_with_embeddings: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/utils/extract-text")
async def extract_text_from_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        # reusing parse_resume to extract text
        data = parse_resume(content, file.filename)
        return {"filename": file.filename, "text": data['raw_text']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class GenerateJDRequest(BaseModel):
    role: str
    experience: str
    skills: str

@app.post("/utils/generate-jd")
async def generate_jd_endpoint(req: GenerateJDRequest):
    try:
        jd_text = resume_agent.generate_job_description(req.role, req.experience, req.skills)
        return {"jd_text": jd_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class MatchRequest(BaseModel):
    jd_text: str
    top_k: int = 5
    job_id: Optional[str] = None

@app.post("/resume/match")
def match_resumes_to_jd(req: MatchRequest):
    try:
        results = matcher_service.match_resumes(req.jd_text, req.top_k, job_id=req.job_id)
        return {"matches": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Phase 3: Scheduling ---
def _is_placeholder_candidate_name(name: Optional[str]) -> bool:
    value = (name or "").strip().lower()
    return value in ("", "candidate", "unknown", "n/a", "na", "-")


def _resolve_candidate_payload(candidate_email: str, candidate_name: Optional[str]) -> Dict[str, str]:
    normalized_email = (candidate_email or "").strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Candidate email is required")

    if not _is_placeholder_candidate_name(candidate_name):
        return {"email": normalized_email, "name": str(candidate_name).strip()}

    resolved_name = ""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT candidate_name
                FROM resume_data
                WHERE LOWER(TRIM(email)) = %s
                  AND candidate_name IS NOT NULL
                  AND TRIM(candidate_name) <> ''
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (normalized_email,),
            )
            row = cur.fetchone()
            if row and row[0] and str(row[0]).strip():
                resolved_name = str(row[0]).strip()
    except Exception:
        # Best-effort name enrichment; scheduler has additional fallback logic.
        resolved_name = ""
    finally:
        if conn:
            conn.close()

    if not resolved_name:
        local_part = normalized_email.split("@", 1)[0].strip().lower()
        if local_part:
            resolved_name = " ".join(
                part
                for part in local_part.replace(".", " ").replace("_", " ").replace("-", " ").split()
                if part
            ).title()

    return {"email": normalized_email, "name": resolved_name or "Candidate"}


class ScheduleRequest(BaseModel):
    candidate_email: str
    candidate_name: Optional[str] = None
    interviewer_id: int
    slot_iso: str

@app.post("/interview/schedule")
def schedule_interview(req: ScheduleRequest):
    try:
        candidate_data = _resolve_candidate_payload(req.candidate_email, req.candidate_name)
        interview_id, created_new = scheduler.schedule_interview(candidate_data, req.interviewer_id, req.slot_iso)
        if created_new:
            log_phase_completion(
                "Interview Scheduling",
                f"candidate={candidate_data['email']} interview_id={interview_id}",
            )
            return {"status": "scheduled", "interview_id": interview_id}

        return {
            "status": "already_scheduled",
            "interview_id": interview_id,
            "message": "Candidate already has an active interview schedule",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/interview/availability/{interviewer_id}")
def get_availability(interviewer_id: int, date: str):
    return scheduler.get_availability(interviewer_id, date)


class SlotOptionsRequest(BaseModel):
    interviewer_ids: List[int]
    days_ahead: int = 1
    search_window_days: int = 3
    num_options: int = 5

@app.post("/interview/slot-options")
def get_slot_options(req: SlotOptionsRequest):
    """Return cross-matched slot options for a panel of interviewers."""
    try:
        slots = scheduler.generate_candidate_slot_options(
            req.interviewer_ids,
            req.days_ahead,
            req.num_options,
            req.search_window_days,
        )
        return {"slots": slots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AssignPanelRequest(BaseModel):
    job_title: str = ""
    round_number: int = 1

@app.post("/interview/assign-panel")
def assign_panel(req: AssignPanelRequest):
    """
    Return the panel template and load-balanced interviewer for a given job role and round.
    """
    try:
        template = scheduler.get_panel_template(req.job_title)
        round_info = next(
            (r for r in template if r["round"] == req.round_number), template[0]
        )
        interviewer = scheduler.get_load_balanced_interviewer(
            department=round_info.get("department")
        )
        return {"round_info": round_info, "assigned_interviewer": interviewer, "full_template": template}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RescheduleRequest(BaseModel):
    interview_id: int
    candidate_email: str
    candidate_name: Optional[str] = None
    new_slot_iso: str

@app.post("/interview/reschedule")
def reschedule_interview(req: RescheduleRequest):
    """Re-schedule an existing interview to a new slot and re-notify the candidate."""
    try:
        candidate_data = _resolve_candidate_payload(req.candidate_email, req.candidate_name)
        success = scheduler.reschedule_interview(req.interview_id, candidate_data, req.new_slot_iso)
        if success:
            log_phase_completion(
                "Interview Rescheduling",
                f"candidate={candidate_data['email']} interview_id={req.interview_id}",
            )
        return {"status": "rescheduled", "interview_id": req.interview_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class NoShowRequest(BaseModel):
    interview_id: int

@app.post("/interview/no-show")
def flag_no_show(req: NoShowRequest):
    """Flag a candidate as a no-show for the given interview."""
    try:
        scheduler.flag_no_show(req.interview_id)
        return {"status": "no_show_flagged", "interview_id": req.interview_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/interview/check-no-shows")
def check_no_shows(grace_minutes: int = 15):
    """
    Scan for scheduled interviews that started more than `grace_minutes` ago
    and auto-flag them as no-shows.  Called periodically by n8n.
    """
    try:
        flagged = scheduler.get_no_show_interviews(grace_minutes)
        results = []
        for interview in flagged:
            scheduler.flag_no_show(interview["id"])
            results.append(interview["id"])
        return {"flagged_count": len(results), "interview_ids": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/interview/send-feedback-kits")
def send_feedback_kits(window_minutes: int = 15):
    """
    Find interviews that just ended and dispatch the interviewer kit / scorecard link.
    Called every minute by the n8n reminder trigger.
    """
    try:
        interviews = scheduler.get_interviews_ready_for_feedback(window_minutes)
        sent = []
        for iv in interviews:
            scheduler.send_interviewer_kit(
                interviewer_email=iv["interviewer_email"],
                interviewer_name=iv["interviewer_name"],
                candidate_name=iv["candidate_name"],
                candidate_email=iv["candidate_email"],
                scheduled_time=str(iv["scheduled_time"]),
            )
            sent.append(iv["interview_id"])
        if sent:
            log_phase_completion(
                "Feedback Kit Dispatch",
                f"kits_sent={len(sent)} interviews={sent}",
            )
        return {"kits_sent": len(sent), "interview_ids": sent}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/interview/decision/{interview_id}")
def apply_decision(interview_id: int):
    """
    Aggregate all feedback for an interview and trigger next action:
    pass → send next-round email, fail → send rejection, hold → flag for HR review.
    """
    try:
        decision = scheduler.aggregate_feedback_and_decide(interview_id)

        # Fetch candidate info
        conn = get_db_connection()
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT candidate_name, candidate_email FROM interview_schedules WHERE id = %s",
                (interview_id,),
            )
            row = cur.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Interview not found")

        candidate_name = row["candidate_name"]
        candidate_email = row["candidate_email"]

        if decision == "fail":
            scheduler.send_rejection_email(candidate_name, candidate_email)
        elif decision == "pass":
            scheduler.send_next_round_email(
                candidate_name, candidate_email,
                next_round_number=1, next_round_label="HR Round"
            )

        log_phase_completion(
            "Interview Decision",
            f"interview_id={interview_id} candidate={candidate_email} decision={decision}",
        )

        return {"decision": decision, "interview_id": interview_id, "candidate": candidate_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Phase 4: Feedback ---
class FeedbackRequest(BaseModel):
    interview_id: int
    technical_skills: int
    communication_skills: int
    overall_rating: int
    recommendation: str
    detailed_feedback: str


class FeedbackCollectRequest(BaseModel):
    interview_id: Optional[int] = None
    candidate_email: Optional[str] = None
    candidate_name: Optional[str] = None
    round_label: Optional[str] = None
    technical_score: int
    communication_score: int
    cultural_fit_score: Optional[int] = None
    overall_rating: int
    recommendation: str
    comments: str


def trigger_feedback_collection_workflow(feedback_payload: Dict) -> Dict:
    """
    Trigger n8n workflow after feedback submission.
    Returns trigger metadata for observability.
    """
    webhook_url = os.getenv(
        "N8N_FEEDBACK_COLLECTION_WEBHOOK",
        "http://localhost:5678/webhook/feedback-collection",
    )

    try:
        response = requests.post(webhook_url, json=feedback_payload, timeout=8)
        return {
            "workflow_triggered": response.status_code < 500,
            "workflow_status_code": response.status_code,
            "workflow_webhook": webhook_url,
        }
    except Exception as exc:
        print(f"Feedback workflow trigger failed: {exc}")
        return {
            "workflow_triggered": False,
            "workflow_status_code": None,
            "workflow_webhook": webhook_url,
            "workflow_error": str(exc),
        }

@app.post("/interview/feedback")
def submit_feedback(req: FeedbackRequest):
    try:
        feedback_service.submit_feedback(req.interview_id, req.model_dump())
        log_phase_completion(
            "Interview Feedback",
            f"interview_id={req.interview_id}",
        )
        return {"status": "submitted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/interview/feedback/collect")
def collect_feedback(req: FeedbackCollectRequest):
    """
    Accept feedback form submissions and map them to the canonical feedback schema.
    Supports lookup by interview_id or candidate_email.
    """
    conn = None
    try:
        interview_id = req.interview_id

        if interview_id is None:
            if not req.candidate_email:
                raise HTTPException(
                    status_code=400,
                    detail="Provide interview_id or candidate_email",
                )

            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id
                    FROM interview_schedules
                    WHERE LOWER(candidate_email) = LOWER(%s)
                      AND feedback_submitted = FALSE
                    ORDER BY scheduled_time DESC
                    LIMIT 1
                    """,
                    (req.candidate_email,),
                )
                row = cur.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="No pending interview found for this candidate",
                )
            interview_id = row[0]

        recommendation_map = {
            "accept": "strong_yes",
            "on_hold": "hold",
            "reject": "strong_no",
        }
        normalized_recommendation = recommendation_map.get(
            str(req.recommendation or "").strip().lower(),
            str(req.recommendation or "").strip().lower() or "hold",
        )

        details = (req.comments or "").strip()
        if req.cultural_fit_score is not None:
            details = f"Cultural Fit Score: {req.cultural_fit_score}/5\n\n{details}".strip()

        payload = {
            "technical_skills": req.technical_score,
            "communication_skills": req.communication_score,
            "overall_rating": req.overall_rating,
            "recommendation": normalized_recommendation,
            "detailed_feedback": details,
        }
        feedback_service.submit_feedback(interview_id, payload)
        log_phase_completion(
            "Interview Feedback",
            f"interview_id={interview_id} source=feedback_form",
        )
        workflow_result = trigger_feedback_collection_workflow(
            {
                "interview_id": interview_id,
                "candidate_email": req.candidate_email,
                "candidate_name": req.candidate_name,
                "round_label": req.round_label,
                "technical_score": req.technical_score,
                "communication_score": req.communication_score,
                "cultural_fit_score": req.cultural_fit_score,
                "overall_rating": req.overall_rating,
                "recommendation": normalized_recommendation,
                "comments": req.comments,
                "source": "feedback_form",
            }
        )

        return {
            "status": "submitted",
            "interview_id": interview_id,
            **workflow_result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

# --- Interview Status ---
@app.get("/jobs/interviewstatus")
def get_interview_status_main():
    """Get comprehensive interview status for all candidates."""
    import traceback
    from backend.database import get_db_connection

    def _derive_name_from_email(raw_email: Optional[str]) -> str:
        email = (raw_email or "").strip().lower()
        if "@" not in email:
            return ""
        local = email.split("@", 1)[0]
        pretty = " ".join(local.replace(".", " ").replace("_", " ").replace("-", " ").split())
        return pretty.title() if pretty else ""

    conn = None
    try:
        # Keep dashboard resilient when n8n inserted placeholder interview rows.
        _repair_incomplete_scheduled_interviews()

        print("--> DEBUG: Attempting to get DB connection for interview status...")
        conn = get_db_connection()
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print("--> DEBUG: Running interview status query...")
            cur.execute("""
                SELECT 
                    i.id as interview_id,
                    i.candidate_name,
                    i.candidate_email,
                    i.scheduled_time,
                    i.status as interview_status,
                    i.feedback_submitted,
                    i.created_at,
                    inv.name as interviewer_name,
                    inv.email as interviewer_email,
                    f.overall_rating,
                    f.recommendation,
                    f.detailed_feedback
                FROM interview_schedules i
                LEFT JOIN interviewers inv ON i.interviewer_id = inv.id
                LEFT JOIN interview_feedback f ON i.id = f.interview_id
                ORDER BY i.scheduled_time DESC
            """)
            rows = cur.fetchall()
            print(f"--> DEBUG: Found {len(rows)} interview rows")

            missing_name_emails = sorted(
                {
                    str((r.get("candidate_email") or "")).strip().lower()
                    for r in rows
                    if str((r.get("candidate_email") or "")).strip()
                    and (
                        not str((r.get("candidate_name") or "")).strip()
                        or str((r.get("candidate_name") or "")).strip().lower() == "candidate"
                    )
                }
            )

            resume_name_by_email = {}
            if missing_name_emails:
                cur.execute(
                    """
                    SELECT LOWER(TRIM(email)) AS normalized_email,
                           MAX(NULLIF(TRIM(candidate_name), '')) AS resume_name
                    FROM resume_data
                    WHERE email IS NOT NULL
                      AND TRIM(email) <> ''
                      AND LOWER(TRIM(email)) = ANY(%s)
                    GROUP BY LOWER(TRIM(email))
                    """,
                    (missing_name_emails,),
                )
                for r in cur.fetchall():
                    normalized_email = str((r.get("normalized_email") or "")).strip().lower()
                    resume_name = str((r.get("resume_name") or "")).strip()
                    if normalized_email and resume_name and resume_name.lower() != "candidate":
                        resume_name_by_email[normalized_email] = resume_name

        now = datetime.now(timezone.utc)
        interviews = []
        for row in rows:
            iv = dict(row)

            email = str(iv.get("candidate_email") or "").strip().lower()
            existing_name = str(iv.get("candidate_name") or "").strip()
            if not existing_name or existing_name.lower() == "candidate":
                iv["candidate_name"] = (
                    resume_name_by_email.get(email)
                    or _derive_name_from_email(email)
                    or "Candidate"
                )

            if iv.get("scheduled_time") is None and iv.get("created_at") is not None:
                iv["scheduled_time"] = iv.get("created_at")

            sched = iv['scheduled_time']
            original_status = (iv.get('interview_status') or '').strip().lower()
            # Normalise to UTC-aware datetime
            if sched is not None:
                if sched.tzinfo is None:
                    sched = sched.replace(tzinfo=timezone.utc)
                end_time = sched + timedelta(hours=1)
                # Keep workflow-driven feedback states visible in the completed section.
                stored = (iv['interview_status'] or '').lower()
                if stored in (
                    'feedback_accepted',
                    'feedback_rejected',
                    'feedback_on_hold',
                    'decision_pass',
                    'decision_fail',
                    'decision_hold',
                ) or iv['feedback_submitted']:
                    iv['interview_status'] = 'completed'
                # Only override if the stored status is not already cancelled/completed-with-feedback
                if stored not in ('cancelled',) and not iv['feedback_submitted']:
                    if sched <= now <= end_time:
                        iv['interview_status'] = 'in_progress'
                    elif now > end_time and stored == 'scheduled':
                        iv['interview_status'] = 'completed'

            # If a row still has an unrecognized status, make it visible in the dashboard
            # instead of leaving it in an unrendered bucket.
            if iv.get('interview_status') not in ('scheduled', 'in_progress', 'completed', 'cancelled'):
                if iv.get('feedback_submitted') or original_status in (
                    'feedback_accepted',
                    'feedback_rejected',
                    'feedback_on_hold',
                    'decision_pass',
                    'decision_fail',
                    'decision_hold',
                ):
                    iv['interview_status'] = 'completed'
                elif sched is not None:
                    iv['interview_status'] = 'scheduled'
                else:
                    iv['interview_status'] = 'in_progress'
            interviews.append(iv)

        # Categorise by computed status
        scheduled   = [i for i in interviews if i.get('interview_status') == 'scheduled']
        in_progress = [i for i in interviews if i.get('interview_status') == 'in_progress']
        completed   = [i for i in interviews if i.get('interview_status') == 'completed']
        cancelled   = [i for i in interviews if i.get('interview_status') == 'cancelled']

        result = {
            "total_interviews": len(interviews),
            "scheduled":        scheduled,
            "in_progress":      in_progress,
            "completed":        completed,
            "cancelled":        cancelled,
            "all_interviews":   interviews,
            "with_feedback":    sum(1 for i in interviews if i.get('feedback_submitted')),
            "pending_feedback": sum(1 for i in interviews if i.get('interview_status') in ('completed', 'in_progress') and not i.get('feedback_submitted'))
        }
        print(f"--> DEBUG: Returning interview status result summary: total={result['total_interviews']}")
        return result
    except Exception as e:
        print(f"CRITICAL ERROR in get_interview_status_main: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.delete("/jobs/clear-interviews")
def clear_all_interviews():
    """Remove all interview schedule records (for cleanup / demo reset)."""
    from backend.database import get_db_connection
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE interview_schedules RESTART IDENTITY CASCADE;")
        conn.commit()
        return {"cleared": True, "message": "All interview records removed."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# --- Phase 5: Onboarding ---
class OnboardingRequest(BaseModel):
    candidate_email: str
    role: str
    start_date: str
    salary: str

@app.post("/onboarding/initiate")
def initiate_onboarding(req: OnboardingRequest):
    try:
        success = onboarding_service.initiate_onboarding(req.candidate_email, req.model_dump())
        if success:
            log_phase_completion(
                "Onboarding",
                f"candidate={req.candidate_email} start_date={req.start_date}",
            )
            return {"status": "onboarding_started"}
        else:
            raise HTTPException(status_code=404, detail="Candidate not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Feedback Form Endpoint ---
@app.get("/feedback-form.html", response_class=HTMLResponse)
async def serve_feedback_form():
    """Serve the interview feedback form HTML page."""
    try:
        backend_root = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(backend_root)

        # Prefer project frontend file for local runs; fallback to backend copy for Docker image.
        candidate_paths = [
            os.path.join(project_root, "frontend", "feedback-form.html"),
            os.path.join(backend_root, "feedback-form.html"),
        ]

        form_path = next((p for p in candidate_paths if os.path.exists(p)), None)
        if not form_path:
            raise HTTPException(status_code=404, detail="Feedback form not found")

        with open(form_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        return HTMLResponse(content=html_content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Set PYTHONPATH for reload subprocesses to find 'backend' module
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.environ["PYTHONPATH"] = project_root + os.pathsep + os.environ.get("PYTHONPATH", "")

    # Run with reload enabled
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

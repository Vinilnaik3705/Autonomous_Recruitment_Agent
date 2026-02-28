import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
import traceback

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from backend.services.resume_service import parse_resume, save_resume_to_db, save_resumes_batch
from backend.database import get_db_connection
from backend.routers import email_router
from fastapi.middleware.cors import CORSMiddleware

# Simple in-memory response cache for high-frequency endpoints
_response_cache: Dict[str, tuple] = {}  # {key: (response, timestamp)}
_cache_ttl_seconds = 5  # Cache responses for 5 seconds

def get_cached_response(cache_key: str):
    """Get cached response if it exists and is not expired."""
    if cache_key in _response_cache:
        response, timestamp = _response_cache[cache_key]
        if (datetime.now(timezone.utc) - timestamp).total_seconds() < _cache_ttl_seconds:
            return response
        else:
            del _response_cache[cache_key]
    return None

def cache_response(cache_key: str, response: dict):
    """Cache a response with current timestamp."""
    _response_cache[cache_key] = (response, datetime.now(timezone.utc))

app = FastAPI(title="HR Automation Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(email_router.router)
from backend.routers import job_router, auth_router, candidate_router, payment_router
app.include_router(job_router.router)
app.include_router(auth_router.router)
app.include_router(candidate_router.router)
app.include_router(payment_router.router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"!!! GLOBAL ERROR: {exc}\n{traceback.format_exc()}"
    print(error_msg)
    # Log to a file as well for easier retrieval
    try:
        with open("backend_errors.log", "a") as f:
            f.write(f"\n[{datetime.now()}] {error_msg}\n")
    except Exception: pass
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
    )

class COOPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
        return response

app.add_middleware(COOPMiddleware)

@app.on_event("startup")
async def startup_event():
    print("--> STARTUP: Listing all registered routes:")
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"   Route: {route.path}")
    print("------------------------------------------")
    
    # One-time database initialization
    try:
        from backend.routers.auth_router import ensure_users_table
        conn = get_db_connection()
        ensure_users_table(conn)
        conn.close()
        print("--> DATABASE: Users table verified and initialized.")
    except Exception as e:
        print(f"--> DATABASE ERROR: Failed to initialize users table: {e}")

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
# Health Check
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running"}

# --- Notifications ---
class Notification(BaseModel):
    type: str = "info"
    title: str
    message: str

@app.get("/notifications")
def get_notifications():
    from backend.database import get_db_connection, close_db
    conn = None
    try:
        conn = get_db_connection()
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 50")
            return cur.fetchall()
    finally:
        if conn: close_db(conn)

@app.post("/notifications")
def create_notification(notif: Notification):
    from backend.database import get_db_connection, close_db
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO notifications (type, title, message) VALUES (%s, %s, %s) RETURNING id",
                (notif.type, notif.title, notif.message)
            )
            notif_id = cur.fetchone()[0]
        conn.commit()
        return {"status": "success", "id": notif_id}
    finally:
        if conn: close_db(conn)

@app.patch("/notifications/{notif_id}/read")
def mark_notification_read(notif_id: int):
    from backend.database import get_db_connection, close_db
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE notifications SET read = TRUE WHERE id = %s", (notif_id,))
        conn.commit()
        return {"status": "success"}
    finally:
        if conn: close_db(conn)

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

@app.post("/resume/sentiment")
async def resume_sentiment(file: UploadFile = File(...)):
    try:
        content = await file.read()
        data = parse_resume(content, file.filename)
        analysis = resume_agent.analyze_sentiment_and_summary(data['raw_text'])
        return {"filename": file.filename, "analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SentimentTextRequest(BaseModel):
    resume_text: str

@app.post("/resume/sentiment-text")
def sentiment_text(req: SentimentTextRequest):
    try:
        analysis = resume_agent.analyze_sentiment_and_summary(req.resume_text)
        return {"status": "success", "analysis": analysis}
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
class ScheduleRequest(BaseModel):
    candidate_email: str
    candidate_name: str
    interviewer_id: int
    slot_iso: str

@app.post("/interview/schedule")
def schedule_interview(req: ScheduleRequest):
    try:
        # Construct dict expected by service
        candidate_data = {"email": req.candidate_email, "name": req.candidate_name}
        interview_id = scheduler.schedule_interview(candidate_data, req.interviewer_id, req.slot_iso)
        return {"status": "scheduled", "interview_id": interview_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/interview/availability/{interviewer_id}")
def get_availability(interviewer_id: int, date: str):
    return scheduler.get_availability(interviewer_id, date)


class SlotOptionsRequest(BaseModel):
    interviewer_ids: List[int]
    days_ahead: int = 2
    num_options: int = 5

@app.post("/interview/slot-options")
def get_slot_options(req: SlotOptionsRequest):
    """Return cross-matched slot options for a panel of interviewers."""
    try:
        slots = scheduler.generate_candidate_slot_options(
            req.interviewer_ids, req.days_ahead, req.num_options
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
    candidate_name: str
    new_slot_iso: str

@app.post("/interview/reschedule")
def reschedule_interview(req: RescheduleRequest):
    """Re-schedule an existing interview to a new slot and re-notify the candidate."""
    try:
        candidate_data = {"email": req.candidate_email, "name": req.candidate_name}
        success = scheduler.reschedule_interview(req.interview_id, candidate_data, req.new_slot_iso)
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
            scheduler.mark_kit_as_sent(iv["interview_id"])
            sent.append(iv["interview_id"])
        return {"kits_sent": len(sent), "interview_ids": sent}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/interview/decision/{interview_id}")
def apply_decision(interview_id: int):
    """
    Aggregate all feedback for an interview and trigger next action:
    pass → send next-round email, fail → send rejection, hold → flag for HR review.
    """
    conn = None
    try:
        decision = scheduler.aggregate_feedback_and_decide(interview_id)

        # Fetch candidate info
        from backend.database import close_db
        conn = get_db_connection()
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT candidate_name, candidate_email FROM interview_schedules WHERE id = %s",
                (interview_id,),
            )
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Interview not found")

        candidate_name = row["candidate_name"]
        candidate_email = row["candidate_email"]

        if decision == "fail":
            scheduler.send_rejection_email(candidate_name, candidate_email)
        elif decision == "pass":
            scheduler.send_next_round_email(
                candidate_name, candidate_email,
                next_round_number=2, next_round_label="Technical Round"
            )

        return {"decision": decision, "interview_id": interview_id, "candidate": candidate_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db(conn)


# --- Phase 4: Feedback ---
class FeedbackRequest(BaseModel):
    interview_id: int
    technical_skills: int
    communication_skills: int
    overall_rating: int
    recommendation: str
    detailed_feedback: str

@app.post("/interview/feedback")
def submit_feedback(req: FeedbackRequest):
    try:
        feedback_service.submit_feedback(req.interview_id, req.model_dump())
        return {"status": "submitted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Interview Status ---
@app.get("/jobs/interviewstatus")
def get_interview_status_main():
    """Get comprehensive interview status for all candidates."""
    import traceback
    from backend.database import get_db_connection, close_db
    
    # Try to return cached response first to prevent DB spam
    cached = get_cached_response("interview_status")
    if cached is not None:
        return cached
    
    conn = None
    try:
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

        now = datetime.now(timezone.utc)
        interviews = []
        for row in rows:
            iv = dict(row)
            sched = iv['scheduled_time']
            # Normalise to UTC-aware datetime
            if sched is not None:
                if sched.tzinfo is None:
                    sched = sched.replace(tzinfo=timezone.utc)
                end_time = sched + timedelta(hours=1)
                # Only override if the stored status is not already cancelled/completed-with-feedback
                stored = iv['interview_status']
                if stored not in ('cancelled',) and not iv['feedback_submitted']:
                    if sched <= now <= end_time:
                        iv['interview_status'] = 'in_progress'
                    elif now > end_time and stored == 'scheduled':
                        iv['interview_status'] = 'completed'
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
            "with_feedback":    sum(1 for i in interviews if i.get('feedback_submitted')),
            "pending_feedback": sum(1 for i in interviews if i.get('interview_status') in ('completed', 'in_progress') and not i.get('feedback_submitted')),
            "status": "connected"
        }
        print(f"--> DEBUG: Returning interview status result summary: total={result['total_interviews']}")
        cache_response("interview_status", result)
        return result
    except Exception as e:
        print(f"CRITICAL ERROR in get_interview_status_main: {str(e)}")
        # Return cached response if available, even if expired
        if "interview_status" in _response_cache:
            response, _ = _response_cache["interview_status"]
            response["status"] = "cached"  # Indicate this is cached data
            return response
        # Return mock data when database is offline (for development/testing)
        mock_response = {
            "total_interviews": 0,
            "scheduled": [],
            "in_progress": [],
            "completed": [],
            "cancelled": [],
            "with_feedback": 0,
            "pending_feedback": 0,
            "status": "offline",
            "message": "Database is offline. Start PostgreSQL with: docker-compose up -d",
            "note": "Showing mock data for development purposes"
        }
        return mock_response
    finally:
        close_db(conn)


@app.delete("/jobs/clear-interviews")
def clear_all_interviews():
    """Remove all interview schedule records (for cleanup / demo reset)."""
    from backend.database import get_db_connection, close_db
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE interview_schedules RESTART IDENTITY CASCADE;")
        conn.commit()
        return {"cleared": True, "message": "All interview records removed."}
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db(conn)

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
        import os
        # Construct path to frontend/feedback-form.html
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        form_path = os.path.join(project_root, "frontend", "feedback-form.html")
        
        if not os.path.exists(form_path):
            raise HTTPException(status_code=404, detail="Feedback form not found")
        
        with open(form_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Set PYTHONPATH for reload subprocesses to find 'backend' module
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.environ["PYTHONPATH"] = project_root + os.pathsep + os.environ.get("PYTHONPATH", "")

    # Run with reload enabled
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

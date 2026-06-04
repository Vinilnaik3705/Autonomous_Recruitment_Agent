"""
Candidate router — read-only portal endpoints for job candidates.
Each candidate can only see their own data (matched by email from the users table).
"""
from fastapi import APIRouter, HTTPException, status, Depends
from psycopg2.extras import RealDictCursor
from backend.database import get_db_connection
from backend.auth import get_current_user

router = APIRouter(prefix="/candidate", tags=["candidate"])

def _require_candidate(current_user: dict):
    """Raise 403 if the caller is not a student (hr bypasses for testing)."""
    if current_user.get("role") not in ("student", "hr"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to candidates only",
        )

@router.get("/my-status")
async def get_my_status(current_user: dict = Depends(get_current_user)):
    """
    Return the logged-in candidate's application status, interview details,
    and timeline stage.  AI scores are intentionally withheld.
    """
    _require_candidate(current_user)

    user_id = current_user.get("user_id")
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("SELECT email FROM users WHERE id = %s", (user_id,))
            user_row = cur.fetchone()
            if not user_row:
                raise HTTPException(status_code=404, detail="User account not found")

            candidate_email = user_row["email"]

            cur.execute(
                """
                SELECT
                    id,
                    candidate_name,
                    email,
                    phone,
                    skills,
                    interview_status,
                    resume_url,
                    created_at,
                    job_id
                FROM resume_data
                WHERE email = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (candidate_email,),
            )
            resume = cur.fetchone()

            if not resume:
                return {
                    "found": False,
                    "email": candidate_email,
                    "message": "No application found for your email address.",
                }

            job_title = None
            job_id = resume.get("job_id")
            if job_id:
                cur.execute(
                    """
                    SELECT title
                    FROM job_descriptions
                    WHERE job_id = %s
                    LIMIT 1
                    """,
                    (job_id,),
                )
                job_row = cur.fetchone()
                if job_row:
                    job_title = job_row.get("title")

            cur.execute(
                """
                SELECT
                    i.id            AS interview_id,
                    i.scheduled_time,
                    i.status        AS interview_status,
                    i.google_event_id,
                    iv.name         AS interviewer_name
                FROM interview_schedules i
                LEFT JOIN interviewers iv ON iv.id = i.interviewer_id
                WHERE i.candidate_email = %s
                ORDER BY i.scheduled_time DESC
                LIMIT 1
                """,
                (candidate_email,),
            )
            interview = cur.fetchone()

            status_val = (resume["interview_status"] or "APPLIED").upper()
            timeline = _build_timeline(status_val)

            return {
                "found": True,
                "application": {
                    "candidate_name": resume["candidate_name"],
                    "email": resume["email"],
                    "phone": resume["phone"],
                    "skills": resume["skills"],
                    "status": status_val,
                    "resume_url": resume["resume_url"],
                    "applied_at": resume["created_at"].isoformat() if resume["created_at"] else None,
                    "job_title": job_title,
                    "job_id": job_id,
                },
                "interview": _format_interview(interview),
                "timeline": timeline,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

def _format_interview(interview):
    if not interview:
        return None
    scheduled = interview.get("scheduled_time")
    return {
        "interview_id": interview.get("interview_id"),
        "scheduled_time": scheduled.isoformat() if scheduled else None,
        "status": interview.get("interview_status"),
        "interviewer_name": interview.get("interviewer_name") or "HR Team",
        "google_event_id": interview.get("google_event_id"),
    }

def _build_timeline(status: str):
    """Map DB status string to a 5-step timeline."""
    STAGES = [
        ("APPLIED",              "Applied"),
        ("SCREENED",             "Screened"),
        ("SHORTLISTED",          "Shortlisted"),
        ("INTERVIEW_SCHEDULED",  "Interview Scheduled"),
        ("DECISION",             "Decision"),
    ]

    stage_map = {
        "APPLIED": 0,
        "SCREENED": 1,
        "SHORTLISTED": 2,
        "INTERVIEW_SCHEDULED": 3,
        "SCHEDULED": 3,
        "FEEDBACK_REQUESTED": 3,
        "FEEDBACK_SUBMITTED": 3,
        "NEXT_ROUND": 4,
        "HIRED": 4,
        "REJECTED": 4,
        "ONBOARDING_INITIATED": 4,
    }

    current_idx = stage_map.get(status, 0)

    steps = []
    for i, (key, label) in enumerate(STAGES):
        if i < current_idx:
            state = "completed"
        elif i == current_idx:
            state = "current"
        else:
            state = "pending"
        steps.append({"stage": key, "label": label, "state": state})

    return steps
# v3: added send-shortlist, send-brevo endpoints
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Tuple, Dict
from datetime import datetime, timezone, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import toml
import os
import requests
import pytz
from urllib.parse import urlencode

router = APIRouter(
    prefix="/email",
    tags=["email"]
)

# Load SMTP configuration
def get_smtp_config():
    """Load SMTP configuration from secrets.toml"""
    try:
        config = toml.load("secrets.toml")
        return config.get("email", {})
    except:
        # Fallback for testing
        return {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "test@example.com",
            "sender_password": "test"
        }

class EmailResponse(BaseModel):
    subject: str
    body: str
    recipient_email: str
    recipient_name: str
    skipped: bool = False

class EmailRequest(BaseModel):
    # Optional with defaults — prevents 422 when Postgres returns empty rows
    # (e.g. Reminder Trigger fires every 15 min but no interviews are scheduled)
    candidate_email: Optional[str] = None
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    interviewer_email: Optional[str] = None
    interviewer_name: Optional[str] = None
    recipient_role: Optional[str] = "interviewer"
    # Extended fields for richer templates
    round_number: Optional[int] = 1
    round_label: Optional[str] = "Interview"
    interview_id: Optional[int] = None
    interview_format: Optional[str] = "video call"
    scheduled_time: Optional[str] = None
    meeting_link: Optional[str] = None
    slot_options: Optional[List[str]] = None
    oa_link: Optional[str] = None
    feedback_form_url: Optional[str] = None
    timezone: Optional[str] = None
    role: Optional[str] = None
    job_title: Optional[str] = None
    position: Optional[str] = None


def _format_scheduled_time_for_email(raw_scheduled_time: Optional[str], tz_name: Optional[str] = None) -> str:
    """Convert ISO/UTC schedule strings into readable local time for email content."""
    if not raw_scheduled_time:
        return "To Be Confirmed"

    display_tz_name = (
        tz_name
        or os.getenv("INTERVIEW_DISPLAY_TIMEZONE")
        or os.getenv("APP_TIMEZONE")
        or "Asia/Kolkata"
    )

    try:
        display_tz = pytz.timezone(display_tz_name)
    except Exception:
        display_tz = pytz.timezone("UTC")

    value = str(raw_scheduled_time).strip()
    lowered = value.lower()
    invalid_markers = {
        "invalid datetime",
        "invalid date",
        "nan",
        "none",
        "null",
        "undefined",
        "tbd",
        "to be confirmed",
    }
    if lowered in invalid_markers:
        return "To Be Confirmed"

    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            # If no offset is present, treat input as already in display timezone.
            dt_local = display_tz.localize(dt)
        else:
            dt_local = dt.astimezone(display_tz)

        return dt_local.strftime("%d %b %Y, %I:%M %p (%Z)")
    except Exception:
        # Preserve readable free-text values but hide known invalid placeholders.
        if any(marker in lowered for marker in ("invalid", "nan", "undefined", "none", "null")):
            return "To Be Confirmed"
        return str(raw_scheduled_time)

def _skip_response():
    """Return a safe skip response when candidate data is missing."""
    return {
        "subject": "SKIPPED",
        "body": "No candidate data — empty Postgres result",
        "recipient_email": "none",
        "recipient_name": "none",
        "skipped": True
    }


def _normalize_email(*values: Optional[str]) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text.lower()
    return ""


def _normalize_name(*values: Optional[str], default: str = "Candidate") -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _derive_name_from_email(email: Optional[str], default: str = "Candidate") -> str:
    """Build a readable fallback name from email local-part."""
    if not email:
        return default
    local = str(email).split("@", 1)[0].strip().lower()
    if not local:
        return default
    pretty = " ".join(
        part for part in local.replace(".", " ").replace("_", " ").replace("-", " ").split() if part
    )
    return pretty.title() if pretty else default


def _lookup_candidate_name_from_db(email: Optional[str]) -> Optional[str]:
    """Look up the real candidate name from resume_data or interview_schedules by email."""
    if not email:
        return None
    try:
        from backend.database import get_db_connection
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Try resume_data first (most reliable source of parsed names)
                cur.execute(
                    "SELECT candidate_name FROM resume_data WHERE LOWER(TRIM(email)) = %s AND candidate_name IS NOT NULL AND TRIM(candidate_name) != '' ORDER BY created_at DESC LIMIT 1",
                    (email.strip().lower(),),
                )
                row = cur.fetchone()
                if row and row[0] and row[0].strip():
                    return row[0].strip()

                # Fallback: try candidates table
                cur.execute(
                    "SELECT name FROM candidates WHERE LOWER(TRIM(email)) = %s AND name IS NOT NULL AND TRIM(name) != '' LIMIT 1",
                    (email.strip().lower(),),
                )
                row = cur.fetchone()
                if row and row[0] and row[0].strip():
                    return row[0].strip()
        finally:
            conn.close()
    except Exception as e:
        print(f"[email_router] DB lookup for candidate name failed: {e}")
    return None


def _resolve_candidate_name(candidate_name: Optional[str], candidate_email: Optional[str]) -> str:
    """Resolve the best candidate name using all available sources."""
    # 1. Use provided name if it's a real name
    name = _normalize_name(candidate_name, default="")
    if name and name.strip().lower() not in ("candidate", "unknown", ""):
        return name

    # 2. Look up from database by email
    db_name = _lookup_candidate_name_from_db(candidate_email)
    if db_name and db_name.strip().lower() not in ("candidate", "unknown", ""):
        return db_name

    # 3. Derive from email address
    derived = _derive_name_from_email(candidate_email, default="")
    if derived and derived.strip().lower() not in ("candidate", "unknown", ""):
        return derived

    return "Candidate"

def _get_interview_context(interview_id: Optional[int]) -> Dict[str, Optional[str]]:
    """Fetch candidate/interviewer/schedule fields from interview_schedules by id."""
    if not interview_id:
        return {}
    try:
        from backend.database import get_db_connection
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.candidate_name, s.candidate_email, s.scheduled_time,
                           i.email AS interviewer_email, i.name AS interviewer_name
                    FROM interview_schedules s
                    LEFT JOIN interviewers i ON i.id = s.interviewer_id
                    WHERE s.id = %s
                    LIMIT 1
                    """,
                    (interview_id,),
                )
                row = cur.fetchone()
                if not row:
                    return {}
                return {
                    "candidate_name": row[0],
                    "candidate_email": row[1],
                    "scheduled_time": row[2].isoformat() if row[2] else None,
                    "interviewer_email": row[3],
                    "interviewer_name": row[4],
                }
        finally:
            conn.close()
    except Exception as e:
        print(f"[email_router] interview context lookup failed: {e}")
        return {}

def _is_placeholder_candidate_name(name: Optional[str]) -> bool:
    return str(name or "").strip().lower() in ("", "candidate", "unknown", "n/a", "na")


def _parse_iso_datetime(raw_value: Optional[str]):
    if not raw_value:
        return None
    try:
        value = str(raw_value).strip()
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _as_utc(dt_value: Optional[datetime]) -> Optional[datetime]:
    if not dt_value:
        return None
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc)


def _pick_future_slot(slot_options: Optional[List[str]]) -> Optional[str]:
    if not slot_options:
        return None
    now = datetime.now(timezone.utc)
    best = None
    for slot in slot_options:
        parsed = _as_utc(_parse_iso_datetime(slot))
        if not parsed:
            continue
        if parsed > now and (best is None or parsed < best):
            best = parsed
    return best.isoformat() if best else None

def _get_min_lead_hours() -> int:
    raw = os.getenv("INTERVIEW_MIN_LEAD_HOURS", "24")
    try:
        return max(1, int(raw))
    except Exception:
        return 24


def _generate_fallback_future_time(days_ahead: int = 1) -> str:
    """Generate a fallback interview time 1+ days in the future at 10 AM UTC."""
    future_time = datetime.now(timezone.utc) + timedelta(days=days_ahead)
    # Set to 10 AM UTC on that day
    future_time = future_time.replace(hour=10, minute=0, second=0, microsecond=0)
    return future_time.isoformat()


def _choose_best_scheduled_time(
    context_time: Optional[str],
    slot_options: Optional[List[str]],
    request_time: Optional[str],
) -> Optional[str]:
    """
    Choose a safe confirmed time.
    - Must be in the future with a minimum lead window (24 hours by default).
    - Prefer slot options generated by scheduling logic.
    - Falls back to a generated future time if no valid options exist.
    """
    now = datetime.now(timezone.utc)
    min_allow_hours = _get_min_lead_hours()
    min_allowed = now + timedelta(hours=min_allow_hours)

    def _ok(raw: Optional[str]) -> Optional[datetime]:
        parsed = _as_utc(_parse_iso_datetime(raw))
        return parsed if parsed and parsed >= min_allowed else None

    # 1) Prefer explicit request time from scheduler/workflow payload.
    request_dt = _ok(request_time)
    if request_dt:
        return request_dt.isoformat()

    # 2) Then prefer earliest acceptable slot from slot options.
    best_slot_dt = None
    if slot_options:
        for slot in slot_options:
            parsed = _ok(slot)
            if not parsed:
                continue
            if best_slot_dt is None or parsed < best_slot_dt:
                best_slot_dt = parsed
    if best_slot_dt:
        return best_slot_dt.isoformat()

    # 3) Finally use context only if it satisfies lead-time.
    context_dt = _ok(context_time)
    if context_dt:
        return context_dt.isoformat()

    # 4) If all else fails, generate a fallback time 1 day ahead
    return _generate_fallback_future_time(days_ahead=1)


def _get_interview_context_by_interviewer(interviewer_email: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Fallback when workflow does not send interview_id.
    Pull the nearest active upcoming schedule for the interviewer.
    """
    if not interviewer_email:
        return {}
    try:
        from backend.database import get_db_connection
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.candidate_name, s.candidate_email, s.scheduled_time,
                           i.email AS interviewer_email, i.name AS interviewer_name
                    FROM interview_schedules s
                    JOIN interviewers i ON i.id = s.interviewer_id
                    WHERE LOWER(TRIM(i.email)) = LOWER(TRIM(%s))
                      AND s.status IN ('scheduled', 'in_progress')
                      AND s.scheduled_time >= NOW() - INTERVAL '15 minutes'
                    ORDER BY s.scheduled_time ASC
                    LIMIT 1
                    """,
                    (interviewer_email,),
                )
                row = cur.fetchone()
                if not row:
                    return {}
                return {
                    "candidate_name": row[0],
                    "candidate_email": row[1],
                    "scheduled_time": row[2].isoformat() if row[2] else None,
                    "interviewer_email": row[3],
                    "interviewer_name": row[4],
                }
        finally:
            conn.close()
    except Exception as e:
        print(f"[email_router] interviewer context lookup failed: {e}")
        return {}

def _lookup_latest_shortlisted_candidate() -> Dict[str, Optional[str]]:
    """Best-effort fallback when workflow omits candidate fields."""
    try:
        from backend.database import get_db_connection
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Prioritize candidates marked as 'shortlisted' in interview_status
                cur.execute(
                    """
                    SELECT candidate_name, email
                    FROM resume_data
                    WHERE email IS NOT NULL
                      AND TRIM(email) <> ''
                      AND interview_status = 'shortlisted'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row:
                    return {"candidate_name": row[0], "candidate_email": row[1]}

                # Fallback to high AI scores if no explicit shortlist
                cur.execute(
                    """
                    SELECT candidate_name, email
                    FROM resume_data
                    WHERE email IS NOT NULL
                      AND TRIM(email) <> ''
                      AND ai_score >= 60
                    ORDER BY ai_score DESC, created_at DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row:
                    return {"candidate_name": row[0], "candidate_email": row[1]}

                # Fallback to candidates table
                cur.execute(
                    """
                    SELECT name, email
                    FROM candidates
                    WHERE email IS NOT NULL
                      AND TRIM(email) <> ''
                      AND resume_shortlisted = TRUE
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row:
                    return {"candidate_name": row[0], "candidate_email": row[1]}
        finally:
            conn.close()
    except Exception as e:
        print(f"[email_router] shortlisted fallback lookup failed: {e}")
    return {}


def _repair_interview_row_from_invite(
    interview_id: Optional[int],
    interviewer_email: Optional[str],
    candidate_name: Optional[str],
    candidate_email: Optional[str],
    scheduled_time_iso: Optional[str],
):
    """
    Backfill missing interview_schedules fields from invite payload/context.
    This keeps dashboard and email in sync when workflow sends partial fields.
    """
    try:
        from backend.database import get_db_connection
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                target_id = interview_id
                if not target_id and interviewer_email:
                    cur.execute(
                        """
                        SELECT s.id
                        FROM interview_schedules s
                        JOIN interviewers i ON i.id = s.interviewer_id
                        WHERE LOWER(TRIM(i.email)) = LOWER(TRIM(%s))
                          AND s.status IN ('scheduled', 'in_progress')
                        ORDER BY s.created_at DESC
                        LIMIT 1
                        """,
                        (interviewer_email,),
                    )
                    row = cur.fetchone()
                    target_id = row[0] if row else None

                if not target_id:
                    conn.rollback()
                    return

                cur.execute(
                    """
                    UPDATE interview_schedules
                    SET
                        candidate_name = CASE
                            WHEN candidate_name IS NULL OR TRIM(candidate_name) = '' OR LOWER(TRIM(candidate_name)) IN ('candidate', 'unknown')
                            THEN COALESCE(NULLIF(%s, ''), candidate_name)
                            ELSE candidate_name
                        END,
                        candidate_email = CASE
                            WHEN candidate_email IS NULL OR TRIM(candidate_email) = ''
                            THEN COALESCE(NULLIF(%s, ''), candidate_email)
                            ELSE candidate_email
                        END,
                        scheduled_time = CASE
                            WHEN scheduled_time IS NULL
                              OR scheduled_time <= NOW() + INTERVAL '30 minutes'
                            THEN COALESCE(%s::timestamp, scheduled_time)
                            ELSE scheduled_time
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        (candidate_name or "").strip(),
                        (candidate_email or "").strip().lower(),
                        scheduled_time_iso,
                        target_id,
                    ),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"[email_router] interview row repair skipped: {e}")


def _build_oa_launch_link(raw_oa_link: str, candidate_email: str, candidate_name: str) -> str:
    """Build backend tracking link that redirects to the official OA URL."""
    public_base = (os.getenv("PUBLIC_API_BASE_URL") or "http://localhost:8000").rstrip("/")
    launch_url = f"{public_base}/oa/launch"
    query = urlencode(
        {
            "candidate_email": candidate_email,
            "candidate_name": candidate_name,
            "target": raw_oa_link,
        }
    )
    return f"{launch_url}?{query}"

@router.post("/oa-practice", response_model=EmailResponse)
def get_oa_practice_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()

    oa_link = req.oa_link or os.getenv("DEFAULT_OA_LINK", "https://hackerrank.com/sample-test")

    return {
                "subject": "OA Practice Link - Recruiting Team",
                "body": f"""
                <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
                <div style="max-width:600px;margin:auto;padding:20px;">
                    <div style="background:#2563eb;color:#fff;padding:22px;border-radius:10px 10px 0 0;text-align:center;">
                        <h2 style="margin:0;">Practice Online Assessment</h2>
                    </div>
                    <div style="background:#f9fafb;padding:24px;border-radius:0 0 10px 10px;">
                        <p>Dear <strong>{req.candidate_name}</strong>,</p>
                        <p>Please use the practice assessment link below to get familiar with the test format.</p>
                        <p style="text-align:center;margin:24px 0;">
                            <a href="{oa_link}" style="display:inline-block;padding:12px 24px;background:#2563eb;color:#fff;border-radius:6px;text-decoration:none;font-weight:bold;">Open Practice OA</a>
                        </p>
                        <p>If the button doesn't work, use this link directly:</p>
                        <p><a href="{oa_link}">{oa_link}</a></p>
                        <p>Best regards,<br><strong>Recruiting Team</strong></p>
                    </div>
                </div>
                </body></html>
                """,
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name
    }

@router.post("/oa-original", response_model=EmailResponse)
def get_oa_original_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()

    oa_link = (
        req.oa_link
        or os.getenv("OFFICIAL_OA_LINK")
        or os.getenv("DEFAULT_OA_LINK")
        or "https://hackerrank.com/sample-test"
    )
    tracked_oa_link = _build_oa_launch_link(oa_link, req.candidate_email, req.candidate_name)

    return {
        "subject": "Official Online Assessment Invitation",
                "body": f"""
                <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
                <div style="max-width:600px;margin:auto;padding:20px;">
                    <div style="background:linear-gradient(135deg,#0ea5e9,#2563eb);color:white;padding:26px;border-radius:10px 10px 0 0;text-align:center;">
                        <h1 style="margin:0;font-size:24px;">Official Online Assessment Invitation</h1>
                    </div>
                    <div style="background:#f9fafb;padding:28px;border-radius:0 0 10px 10px;">
                        <p>Dear <strong>{req.candidate_name}</strong>,</p>

                        <p>You have been invited to take the <strong>official Online Assessment</strong>.</p>
                        <p>Please complete it within <strong>48 hours</strong>.</p>

                        <p style="text-align:center;margin:24px 0;">
                            <a href="{tracked_oa_link}" style="display:inline-block;padding:14px 28px;background:#2563eb;color:white;text-decoration:none;border-radius:6px;font-weight:bold;">Start Official OA</a>
                        </p>

                        <p>If the button does not open, copy and paste this link in your browser:</p>
                        <p><a href="{tracked_oa_link}">{tracked_oa_link}</a></p>

                        <p style="font-size:12px;color:#666;">Direct official assessment link (fallback): <a href="{oa_link}">{oa_link}</a></p>

                        <p>Best regards,<br><strong>Recruiting Team</strong></p>
                    </div>
                </div>
                </body></html>
                """,
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name
    }

@router.post("/resume-shortlisted", response_model=EmailResponse)
def get_resume_shortlisted_email(req: EmailRequest):
    candidate_email = _normalize_email(req.candidate_email, req.email)
    candidate_name = _normalize_name(req.candidate_name, req.name)
    role_name = (req.role or req.job_title or req.position or "the applied role").strip()

    if not candidate_email or not candidate_name:
        return _skip_response()

    oa_link = (
        req.oa_link
        or os.getenv("OFFICIAL_OA_LINK")
        or os.getenv("DEFAULT_OA_LINK")
        or "https://hackerrank.com/sample-test"
    )
    tracked_oa_link = _build_oa_launch_link(oa_link, candidate_email, candidate_name)
    
    # Professional HTML email template
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; padding: 15px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Congratulations!</h1>
            </div>
            <div class="content">
                <p>Dear <strong>{candidate_name}</strong>,</p>
                
                <p>We are pleased to inform you that your resume has been <strong>shortlisted</strong> for further consideration.</p>
                <p><strong>Role:</strong> {role_name}</p>
                
                <p>Your skills and experience align well with our requirements, and we would like to proceed to the next step of our hiring process.</p>
                
                <h3>📋 Next Step: Online Assessment</h3>
                <p>Please complete the Online Assessment using the link below within <strong>48 hours</strong>:</p>
                
                <p style="text-align: center;">
                    <a href="{tracked_oa_link}" class="button">Take Online Assessment</a>
                </p>
                
                <p><strong>Assessment Details:</strong></p>
                <ul>
                    <li>Duration: 60 minutes</li>
                    <li>Topics: Programming, Problem Solving, Technical Skills</li>
                    <li>Deadline: Within 48 hours from receipt of this email</li>
                </ul>
                
                <p>We look forward to reviewing your performance!</p>
                
                <p>Best regards,<br>
                <strong>HR Recruiting Team</strong></p>
            </div>
            <div class="footer">
                <p>This is an automated email from our recruitment system.</p>
                <p>If you have any questions, please reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return {
        "subject": f"Your Resume Has Been Shortlisted - {role_name}",
        "body": html_body,
        "recipient_email": candidate_email,
        "recipient_name": candidate_name
    }

@router.post("/oa-shortlisted", response_model=EmailResponse)
def get_oa_shortlisted_email(req: EmailRequest):
    candidate_email = _normalize_email(req.candidate_email, req.email)
    candidate_name = _normalize_name(req.candidate_name, req.name)

    if not candidate_email or not candidate_name:
        return _skip_response()
    return {
        "subject": "Congratulations! You are Shortlisted",
        "body": "Dear Candidate,\n\nWe are pleased to inform you that you have been shortlisted for the next round.\n\nBest,\nRecruiting Team",
        "recipient_email": candidate_email,
        "recipient_name": candidate_name
    }

@router.post("/interview-confirm", response_model=EmailResponse)
def get_interview_confirm_email(req: EmailRequest):
    candidate_email = _normalize_email(req.candidate_email, req.email)
    candidate_name = _normalize_name(req.candidate_name, req.name)

    if not candidate_email or not candidate_name:
        return _skip_response()
    return {
        "subject": "Interview Confirmation",
        "body": "Dear Candidate,\n\nYour interview has been confirmed. Please check the details in your calendar invitation.\n\nBest,\nRecruiting Team",
        "recipient_email": candidate_email,
        "recipient_name": candidate_name
    }

@router.post("/interview-reminder", response_model=EmailResponse)
def get_interview_reminder_email(req: EmailRequest):
    candidate_email = _normalize_email(req.candidate_email, req.email)
    candidate_name = _normalize_name(req.candidate_name, req.name)

    if not candidate_email or not candidate_name:
        return {
            "subject": "SKIPPED",
            "body": "No candidate data — empty Postgres result",
            "recipient_email": "none",
            "recipient_name": "none",
            "skipped": True
        }
    return {
        "subject": "Interview Reminder",
        "body": "Dear Candidate,\n\nThis is a reminder for your upcoming interview tomorrow.\n\nBest,\nRecruiting Team",
        "recipient_email": candidate_email,
        "recipient_name": candidate_name
    }

@router.post("/interview-invite", response_model=EmailResponse)
def get_interview_invite_email(req: EmailRequest):
    context = _get_interview_context(req.interview_id)
    shortlist_fallback = _lookup_latest_shortlisted_candidate()

    candidate_email = _normalize_email(
        req.candidate_email,
        req.email,
        context.get("candidate_email"),
        shortlist_fallback.get("candidate_email"),
    )
    resolved_name = _resolve_candidate_name(
        req.candidate_name
        or req.name
        or context.get("candidate_name")
        or shortlist_fallback.get("candidate_name"),
        candidate_email,
    )
    candidate_name = resolved_name
    recipient_email = candidate_email
    recipient_name = candidate_name

    if not recipient_email:
        return _skip_response()

    # Never send if we still only have a placeholder candidate identity.
    if _is_placeholder_candidate_name(candidate_name):
        return _skip_response()

    round_number = req.round_number or 1
    round_label = req.round_label or "Interview"
    interview_format = req.interview_format or "video call"
    source_scheduled_time = _choose_best_scheduled_time(
        context_time=context.get("scheduled_time"),
        slot_options=req.slot_options,
        request_time=req.scheduled_time,
    )
    # source_scheduled_time should never be None now due to fallback
    if not source_scheduled_time:
        # Safety fallback - generate 1 day ahead at 10 AM
        source_scheduled_time = _generate_fallback_future_time(days_ahead=1)

    # Persist repaired values so dashboard reads corrected fields too.
    _repair_interview_row_from_invite(
        interview_id=req.interview_id,
        interviewer_email=_normalize_email(req.interviewer_email, context.get("interviewer_email")),
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        scheduled_time_iso=source_scheduled_time,
    )

    scheduled_time = _format_scheduled_time_for_email(source_scheduled_time, req.timezone)
    meeting_section = (
        f'<p><strong>Meeting Link:</strong> <a href="{req.meeting_link}">{req.meeting_link}</a></p>'
        if req.meeting_link
        else "<p><strong>Meeting link:</strong> Will be shared via calendar invitation.</p>"
    )

    slots_html = ""
    if req.slot_options:
        items = "".join(
            f"<li>{_format_scheduled_time_for_email(s, req.timezone)}</li>"
            for s in req.slot_options
        )
        slots_html = f"<p><strong>Available Time Slots (select one):</strong></p><ul>{items}</ul>"

    html_body = f"""
    <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
    <div style="max-width:600px;margin:auto;padding:20px;">
        <div style="background:linear-gradient(135deg,#0f766e,#14b8a6);color:white;padding:30px;border-radius:10px 10px 0 0;text-align:center;">
            <h1>Your Interview Is Scheduled</h1>
            <p style="font-size:18px;opacity:0.9;">Round {round_number}: {round_label}</p>
        </div>
        <div style="background:#f9fafb;padding:30px;border-radius:0 0 10px 10px;">
            <p>Hi <strong>{candidate_name}</strong>,</p>
            <p>Your interview has been scheduled. Please join at the confirmed time below.</p>

            <table style="width:100%;border-collapse:collapse;margin:16px 0;">
                <tr style="background:#edf2f7;">
                    <td style="padding:8px 12px;font-weight:bold;">Role</td>
                    <td style="padding:8px 12px;">{req.job_title or req.position or req.role or 'Interview'}</td>
                </tr>
                <tr>
                    <td style="padding:8px 12px;font-weight:bold;">Confirmed Time</td>
                    <td style="padding:8px 12px;">{scheduled_time}</td>
                </tr>
                <tr style="background:#edf2f7;">
                    <td style="padding:8px 12px;font-weight:bold;">Format</td>
                    <td style="padding:8px 12px;">{interview_format.title()}</td>
                </tr>
                <tr>
                    <td style="padding:8px 12px;font-weight:bold;">Interviewer</td>
                    <td style="padding:8px 12px;">{_normalize_name(req.interviewer_name, context.get('interviewer_name'), default='HR Team')}</td>
                </tr>
            </table>

            {slots_html}
            {meeting_section}

            <h3 style="color:#4a5568;">Join Instructions</h3>
            <ul>
                <li>Join a few minutes early to avoid delays</li>
                <li>Keep your resume and notes ready</li>
                <li>Use the calendar link or meeting link above to join</li>
            </ul>

            <div style="background:#ecfeff;border-left:4px solid #14b8a6;padding:12px;margin:16px 0;border-radius:4px;">
                <strong>Need to reschedule?</strong> Reply to this email or contact HR as soon as possible.
            </div>

            <p>Thank you.</p>
            <br><p>Best regards,<br><strong>HR Recruiting Team</strong></p>
        </div>
        <p style="text-align:center;font-size:12px;color:#888;margin-top:20px;">
            This is an automated email from our recruitment system.
        </p>
    </div>
    </body></html>
    """

    return {
        "subject": f"Your Interview Is Scheduled – Round {round_number}: {round_label} ({candidate_name})",
        "body": html_body,
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
    }


# ── Interviewer kit (sent ~1 hr before the interview) ──────────────────────

class InterviewerKitRequest(BaseModel):
    interviewer_email: str
    interviewer_name: str
    candidate_name: str
    candidate_email: str
    scheduled_time: Optional[str] = None
    round_label: Optional[str] = "Interview"
    meeting_link: Optional[str] = None
    feedback_form_url: Optional[str] = None
    resume_summary: Optional[str] = None
    job_description: Optional[str] = None

class InterviewerKitResponse(BaseModel):
    subject: str
    body: str
    recipient_email: str
    recipient_name: str

@router.post("/interviewer-kit", response_model=InterviewerKitResponse)
def get_interviewer_kit_email(req: InterviewerKitRequest):
    """Return the pre-interview kit email body for an interviewer."""
    candidate_name = _resolve_candidate_name(req.candidate_name, req.candidate_email)

    pretty_scheduled_time = _format_scheduled_time_for_email(req.scheduled_time)
    feedback_url = req.feedback_form_url or "http://localhost:8000/feedback-form.html"
    jd_section = (
        f"<h3>Job Description</h3><p>{req.job_description[:600]}...</p>"
        if req.job_description else ""
    )
    resume_section = (
        f"<h3>Candidate Resume Summary</h3><p>{req.resume_summary[:500]}...</p>"
        if req.resume_summary else ""
    )

    html_body = f"""
    <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
    <div style="max-width:600px;margin:auto;padding:20px;">
      <div style="background:#1a202c;color:white;padding:25px;border-radius:10px 10px 0 0;">
        <h2>🎯 Interview Kit – {req.round_label}</h2>
      </div>
      <div style="background:#f9fafb;padding:25px;border-radius:0 0 10px 10px;">
        <p>Hi <strong>{req.interviewer_name}</strong>,</p>
        <p>You have an upcoming interview. Here are the full details:</p>

        <table style="width:100%;border-collapse:collapse;margin:12px 0;">
          <tr style="background:#edf2f7;">
            <td style="padding:8px 12px;font-weight:bold;">Candidate</td>
                        <td style="padding:8px 12px;">{candidate_name} ({req.candidate_email})</td>
          </tr>
          <tr>
            <td style="padding:8px 12px;font-weight:bold;">Round</td>
            <td style="padding:8px 12px;">{req.round_label}</td>
          </tr>
          <tr style="background:#edf2f7;">
            <td style="padding:8px 12px;font-weight:bold;">Scheduled Time</td>
                        <td style="padding:8px 12px;">{pretty_scheduled_time or 'See calendar invite'}</td>
          </tr>
                    <tr>
                        <td style="padding:8px 12px;font-weight:bold;">Meeting Link</td>
                        <td style="padding:8px 12px;">
                            {'<a href="' + req.meeting_link + '">' + req.meeting_link + '</a>' if req.meeting_link else 'Check calendar invite'}
                        </td>
                    </tr>
        </table>

        {jd_section}
        {resume_section}

        <h3>Suggested Interview Questions</h3>
        <ol>
          <li>Walk me through your most relevant project or achievement.</li>
          <li>Describe a challenging problem you solved – what was your approach?</li>
          <li>How do you prioritise tasks when you have competing deadlines?</li>
          <li>Give an example of constructive feedback you received and how you responded.</li>
          <li>What questions do you have for us about the team / role?</li>
        </ol>

        <h3>Competency Scorecard</h3>
        <p>Please rate the candidate on: Technical Skills, Communication, Problem-Solving,
           Culture Fit and provide an overall recommendation.</p>
        <p>
          <a href="{feedback_url}"
             style="display:inline-block;padding:12px 28px;background:#667eea;color:white;
                    border-radius:5px;text-decoration:none;font-weight:bold;">
            Submit Feedback Scorecard
          </a>
        </p>
        <p style="color:#e53e3e;font-size:13px;">⚠ Please submit within 24 hours of the interview.</p>

        <br><p>Best regards,<br><strong>HR Coordination Team</strong></p>
      </div>
    </div>
    </body></html>
    """

    return {
        "subject": f"Interview Kit: {candidate_name} – {req.round_label}",
        "body": html_body,
        "recipient_email": req.interviewer_email,
        "recipient_name": req.interviewer_name,
    }


# ── Rejection email ──────────────────────────────────────────────────────────

@router.post("/rejection", response_model=EmailResponse)
def get_rejection_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()

    html_body = f"""
    <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
    <div style="max-width:600px;margin:auto;padding:20px;">
      <div style="background:#4a5568;color:white;padding:25px;border-radius:10px 10px 0 0;text-align:center;">
        <h2>Application Status Update</h2>
      </div>
      <div style="background:#f9fafb;padding:25px;border-radius:0 0 10px 10px;">
        <p>Dear <strong>{req.candidate_name}</strong>,</p>
        <p>Thank you sincerely for your time and interest in joining our team. We genuinely enjoyed
           learning more about your experience throughout the interview process.</p>
        <p>After careful deliberation, we have made the difficult decision to move forward with
           another candidate whose background more closely aligns with the specific requirements
           of this role at this time.</p>
        <p>Please know that this decision is in no way a reflection of your abilities. We will keep
           your profile on file and encourage you to apply for future openings that suit your skills.</p>
        <p>We wish you every success in your job search and career.</p>
        <br><p>Warm regards,<br><strong>HR Recruiting Team</strong></p>
      </div>
      <p style="text-align:center;font-size:12px;color:#888;margin-top:20px;">
        This is an automated email. If you have questions, please contact hr@company.com.
      </p>
    </div>
    </body></html>
    """

    return {
        "subject": "Your Application Status – Thank You for Interviewing",
        "body": html_body,
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name,
    }


# ── Next-round advancement email ─────────────────────────────────────────────

class NextRoundRequest(BaseModel):
    candidate_email: Optional[str] = None
    candidate_name: Optional[str] = None
    next_round_number: int = 1
    next_round_label: str = "HR Round"

@router.post("/next-round", response_model=EmailResponse)
def get_next_round_email(req: NextRoundRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()

    html_body = f"""
    <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
    <div style="max-width:600px;margin:auto;padding:20px;">
      <div style="background:linear-gradient(135deg,#48bb78,#276749);color:white;padding:30px;
                  border-radius:10px 10px 0 0;text-align:center;">
        <h1>🎉 You've Advanced to the Next Round!</h1>
      </div>
      <div style="background:#f9fafb;padding:30px;border-radius:0 0 10px 10px;">
        <p>Dear <strong>{req.candidate_name}</strong>,</p>
        <p>Congratulations! We are delighted to let you know that you have successfully
           <strong>passed your recent interview</strong> and are advancing to the next stage
           of our selection process.</p>
        <div style="background:#f0fff4;border-left:4px solid #48bb78;padding:16px;
                    margin:16px 0;border-radius:4px;">
          <strong>Next Step:</strong> Round {req.next_round_number} – {req.next_round_label}
        </div>
        <p>Our team will reach out shortly with scheduling details. Please keep an eye on
           your inbox over the next 24–48 hours.</p>
        <p>Keep up the great work — we look forward to continuing the process with you!</p>
        <br><p>Best regards,<br><strong>HR Recruiting Team</strong></p>
      </div>
    </div>
    </body></html>
    """

    return {
        "subject": f"🎉 You've Advanced – Round {req.next_round_number}: {req.next_round_label}",
        "body": html_body,
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name,
    }


# ── Offer letter notification ─────────────────────────────────────────────────

class OfferLetterRequest(BaseModel):
    candidate_email: Optional[str] = None
    candidate_name: Optional[str] = None
    role: Optional[str] = "the position"
    offer_link: Optional[str] = None

@router.post("/offer-letter", response_model=EmailResponse)
def get_offer_letter_email(req: OfferLetterRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()

    sign_section = (
                f'<div style="margin-top:28px;margin-bottom:24px;">'
                f'<a href="{req.offer_link}" style="display:inline-block;padding:14px 26px;'
                f'background:#0f766e;color:#ffffff;border-radius:8px;text-decoration:none;font-weight:600;">'
                f'Review and Sign Offer Letter</a></div>'
                if req.offer_link
                else "<p style=\"margin:24px 0 0;\">Our team will share the formal offer letter document shortly.</p>"
    )

    html_body = f"""
        <!DOCTYPE html>
        <html>
            <body style="margin:0;padding:0;background:#f5f7fb;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
                <div style="max-width:720px;margin:0 auto;padding:32px 20px;">
                    <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(15,23,42,0.08);">
                        <div style="padding:28px 32px 18px;border-bottom:1px solid #e5e7eb;text-align:center;">
                            <div style="font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#0f766e;font-weight:700;">Offer Letter</div>
                            <h1 style="margin:10px 0 0;font-size:28px;line-height:1.2;color:#111827;">Job Offer from HR Recruiting Team</h1>
                        </div>
                        <div style="padding:32px;line-height:1.7;font-size:15px;">
                            <p style="margin:0 0 18px;">Dear <strong>{req.candidate_name}</strong>,</p>
                            <p style="margin:0 0 18px;">We are pleased to extend a formal offer for the position of <strong>{req.role}</strong> with our team.</p>
                            <div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:12px;padding:18px 20px;margin:0 0 22px;">
                                <p style="margin:0 0 8px;"><strong>Candidate:</strong> {req.candidate_name}</p>
                                <p style="margin:0 0 8px;"><strong>Role:</strong> {req.role}</p>
                                <p style="margin:0;"><strong>Action Required:</strong> Please review the offer and sign electronically at your earliest convenience, ideally within 5 business days.</p>
                            </div>
                            <p style="margin:0 0 18px;">If you have any questions about the role, compensation, or next steps, please reply to this email and our HR team will assist you.</p>
                            <p style="margin:0 0 4px;">We look forward to welcoming you to the team.</p>
                            <p style="margin:0;">Best regards,<br><strong>HR Recruiting Team</strong></p>
                            {sign_section}
                        </div>
                    </div>
                </div>
            </body>
        </html>
    """

    return {
                "subject": f"Offer Letter - {req.role}",
        "body": html_body,
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name,
    }


# ── Reschedule acknowledgement ────────────────────────────────────────────────

@router.post("/reschedule-request", response_model=EmailResponse)
def get_reschedule_request_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()

    html_body = f"""
    <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
    <div style="max-width:600px;margin:auto;padding:20px;">
      <div style="background:#667eea;color:white;padding:25px;border-radius:10px 10px 0 0;text-align:center;">
        <h2>Interview Rescheduled</h2>
      </div>
      <div style="background:#f9fafb;padding:25px;border-radius:0 0 10px 10px;">
        <p>Dear <strong>{req.candidate_name}</strong>,</p>
        <p>Your interview has been <strong>successfully rescheduled</strong>.
           Please check your email for an updated calendar invitation with the new details.</p>
        {"<p><strong>New Time:</strong> " + req.scheduled_time + "</p>" if req.scheduled_time else ""}
        <p>If you have further questions or need to make additional changes, please reply
           to this email.</p>
        <br><p>Best regards,<br><strong>HR Recruiting Team</strong></p>
      </div>
    </div>
    </body></html>
    """

    return {
        "subject": "Your Interview Has Been Rescheduled",
        "body": html_body,
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name,
    }


# ── No-show follow-up ─────────────────────────────────────────────────────────

@router.post("/no-show-followup", response_model=EmailResponse)
def get_no_show_followup_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()

    html_body = f"""
    <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
    <div style="max-width:600px;margin:auto;padding:20px;">
      <div style="background:#e53e3e;color:white;padding:25px;border-radius:10px 10px 0 0;text-align:center;">
        <h2>Missed Interview – Follow Up</h2>
      </div>
      <div style="background:#f9fafb;padding:25px;border-radius:0 0 10px 10px;">
        <p>Dear <strong>{req.candidate_name}</strong>,</p>
        <p>We noticed you were unable to join your scheduled interview today. We understand
           that unexpected situations arise and we hope everything is okay.</p>
        <p>If you are still interested in the position, please reply to this email within
           <strong>48 hours</strong> so we can reschedule at a time that works for you.</p>
        <p>Please note that if we do not hear back, we may need to move forward with other
           candidates.</p>
        <br><p>Best regards,<br><strong>HR Recruiting Team</strong></p>
      </div>
    </div>
    </body></html>
    """

    return {
        "subject": "Missed Interview – We'd Like to Reconnect",
        "body": html_body,
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name,
    }


# ── Feedback reminder to interviewer ─────────────────────────────────────────

class FeedbackReminderRequest(BaseModel):
    interviewer_email: Optional[str] = None
    interviewer_name: Optional[str] = None
    candidate_name: Optional[str] = None
    feedback_form_url: Optional[str] = None

class FeedbackReminderResponse(BaseModel):
    subject: str
    body: str
    recipient_email: str
    recipient_name: str
    skipped: bool = False

@router.post("/feedback-reminder-interviewer", response_model=FeedbackReminderResponse)
def get_feedback_reminder_interviewer_email(req: FeedbackReminderRequest):
    if not req.interviewer_email or not req.interviewer_name:
        return {"subject": "SKIPPED", "body": "No interviewer data", "recipient_email": "none",
                "recipient_name": "none", "skipped": True}

    feedback_url = req.feedback_form_url or "http://localhost:8000/feedback-form.html"
    candidate_text = f"for <strong>{req.candidate_name}</strong>" if req.candidate_name else ""

    html_body = f"""
    <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
    <div style="max-width:600px;margin:auto;padding:20px;">
      <div style="background:#ed8936;color:white;padding:25px;border-radius:10px 10px 0 0;text-align:center;">
        <h2>⏰ Feedback Reminder</h2>
      </div>
      <div style="background:#f9fafb;padding:25px;border-radius:0 0 10px 10px;">
        <p>Hi <strong>{req.interviewer_name}</strong>,</p>
        <p>This is a friendly reminder that your feedback scorecard {candidate_text}
           is still pending submission.</p>
        <p>Timely feedback is crucial to keep the hiring process moving efficiently.
           Please take a few minutes to complete the scorecard now:</p>
        <p>
          <a href="{feedback_url}"
             style="display:inline-block;padding:12px 28px;background:#ed8936;color:white;
                    border-radius:5px;text-decoration:none;font-weight:bold;">
            Submit Feedback Now
          </a>
        </p>
        <p>If you have already submitted, please disregard this message.</p>
        <br><p>Thank you,<br><strong>HR Coordination Team</strong></p>
      </div>
    </div>
    </body></html>
    """

    return {
        "subject": f"⏰ Reminder: Please Submit Your Interview Feedback",
        "body": html_body,
        "recipient_email": req.interviewer_email,
        "recipient_name": req.interviewer_name,
    }

@router.post("/feedback-request", response_model=EmailResponse)
def get_feedback_request_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()
    return {
        "subject": "How was your interview?",
        "body": f"Dear {req.candidate_name},\n\nWe would love to hear your feedback regarding the recent interview process.\n\nBest,\nRecruiting Team",
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name
    }

@router.post("/onboarding-welcome", response_model=EmailResponse)
def get_onboarding_welcome_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()
    return {
        "subject": "Welcome to the Team!",
        "body": f"Dear {req.candidate_name},\n\nCongratulations and welcome aboard! We are excited to have you join us.\n\nBest,\nRecruiting Team",
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name
    }

# ── OA Completion Thank You Email ────────────────────────────────────────────

class OACompletionRequest(BaseModel):
    candidate_email: Optional[str] = None
    candidate_name: Optional[str] = None
    oa_score: Optional[float] = None
    report_url: Optional[str] = None

@router.post("/oa-completion-thank-you", response_model=EmailResponse)
def get_oa_completion_thank_you_email(req: OACompletionRequest):
    """Send thank you email after OA completion with score and next steps."""
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()

    score = float(req.oa_score or 0)
    score_text = f"{score:.2f}".rstrip("0").rstrip(".")
    score_color = "#48bb78" if score >= 6 else "#ed8936"
    score_message = "Congratulations! You have passed the assessment." if score >= 6 else "Thank you for your effort. Our team will review your performance."

    report_section = (
        f'<p style="text-align: center; margin: 24px 0;"><a href="{req.report_url}" '
        f'style="display:inline-block;padding:12px 28px;background:#667eea;color:white;'
        f'border-radius:6px;text-decoration:none;font-weight:bold;">View Your Assessment Report</a></p>'
        if req.report_url
        else ""
    )

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 40px; border-radius: 0 0 10px 10px; }}
            .score-box {{ background: white; border: 3px solid {score_color}; border-radius: 8px; padding: 24px; text-align: center; margin: 24px 0; }}
            .score-value {{ font-size: 48px; color: {score_color}; font-weight: bold; margin: 8px 0; }}
            .score-label {{ font-size: 14px; color: #666; margin: 4px 0; }}
            .next-steps {{ background: #ebf8ff; border-left: 4px solid #667eea; padding: 16px; border-radius: 4px; margin: 20px 0; }}
            .next-steps strong {{ color: #667eea; }}
            .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; border-top: 1px solid #ddd; padding-top: 20px; }}
            ul {{ margin: 12px 0; padding-left: 24px; }}
            li {{ margin: 10px 0; }}
            .header h1 {{ margin: 0; font-size: 28px; }}
            .header p {{ margin: 8px 0 0 0; opacity: 0.95; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Thank You!</h1>
                <p>Your Online Assessment is Complete</p>
            </div>
            <div class="content">
                <p>Dear <strong>{req.candidate_name}</strong>,</p>
                
                <p>Thank you for completing the Online Assessment. We appreciate your time, effort, and commitment to our recruitment process.</p>
                
                <div class="score-box">
                    <div class="score-label">Your Score</div>
                    <div class="score-value">{score_text}/10</div>
                </div>
                
                <p><strong>{score_message}</strong></p>
                
                <p>Your response has been recorded and our recruiting team will thoroughly review your performance. 
                We evaluate candidates based on multiple factors including technical skills, problem-solving approach, and code quality.</p>
                
                {report_section}
                
                <div class="next-steps">
                    <strong>📋 What Happens Next?</strong>
                    <ul>
                        <li>Our team will carefully review your assessment results and coding solutions</li>
                        <li>If you move to the next round, you will be notified within <strong>3-5 business days</strong></li>
                        <li>Please keep an eye on your email for further updates and opportunities</li>
                        <li>We typically send updates on weekdays between 9 AM - 6 PM</li>
                    </ul>
                </div>
                
                <p><strong>💡 Please Note:</strong> Keep this email and your score for your records. You can access your detailed assessment report at any time using the link above.</p>
                
                <p>If you have any questions, concerns, or feedback about the assessment process, please don't hesitate to reach out to our recruiting team. We'd love to hear from you.</p>
                
                <p>We wish you the very best in the recruitment process and look forward to potentially working with you!</p>
                
                <br><p>Warm regards,<br>
                <strong>HR Recruiting Team</strong></p>
            </div>
            <div class="footer">
                <p>This is an automated email from our recruitment system.</p>
                <p>If you believe this was sent in error, please contact us immediately.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return {
        "subject": f"Thank You for Completing Your Assessment – Your Score: {score_text}/10",
        "body": html_body,
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name
    }

class SendEmailRequest(BaseModel):
    recipient_email: str
    recipient_name: str
    subject: str
    body: str
    is_html: Optional[bool] = None

class SendEmailResponse(BaseModel):
    success: bool
    message: str
    recipient_email: str


def _send_email_via_brevo(
    recipient_email: str,
    recipient_name: str,
    subject: str,
    body: str,
    is_html: bool,
    sender_email: str,
    sender_name: str,
    brevo_api_key: str,
) -> Tuple[bool, str]:
    if not brevo_api_key:
        return False, "Brevo API key is missing"
    if not sender_email:
        return False, "Sender email is required for Brevo delivery"

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": recipient_email, "name": recipient_name}],
        "subject": subject,
    }
    if is_html:
        payload["htmlContent"] = body
    else:
        payload["textContent"] = body

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": brevo_api_key,
            },
            json=payload,
            timeout=20,
        )
        if 200 <= response.status_code < 300:
            return True, "Email sent successfully via Brevo"
        detail = response.text[:500]
        try:
            detail = str(response.json())
        except Exception:
            pass
        return False, f"Brevo send failed ({response.status_code}): {detail[:500]}"
    except Exception as exc:
        return False, f"Brevo send failed: {str(exc)}"


def send_email_via_smtp(
    recipient_email: str,
    recipient_name: str,
    subject: str,
    body: str,
    is_html: bool = False,
) -> Tuple[bool, str]:
    """Send an email via configured SMTP server. Returns (success, message)."""
    smtp_config = get_smtp_config()
    sender_email = smtp_config.get("sender_email", "")
    sender_password = smtp_config.get("sender_password", "")
    sender_name = smtp_config.get("sender_name", "HR Recruitment Team")
    brevo_api_key = os.getenv("BREVO_API_KEY") or smtp_config.get("brevo_api_key", "")

    if not sender_email:
        sender_email = os.getenv("BREVO_SENDER_EMAIL", "")

    if not sender_email or not sender_password:
        if brevo_api_key:
            return _send_email_via_brevo(
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                subject=subject,
                body=body,
                is_html=is_html,
                sender_email=sender_email,
                sender_name=sender_name,
                brevo_api_key=brevo_api_key,
            )
        return False, (
            "SMTP credentials are not configured in secrets.toml "
            "(email.sender_email + email.sender_password) and Brevo API fallback is unavailable"
        )

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = recipient_email
    msg["Subject"] = subject

    subtype = "html" if is_html else "plain"
    msg.attach(MIMEText(body, subtype, "utf-8"))

    try:
        server = smtplib.SMTP(
            smtp_config.get("smtp_server", "smtp.gmail.com"),
            int(smtp_config.get("smtp_port", 587)),
        )
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully"
    except Exception as smtp_error:
        if brevo_api_key:
            print(f"SMTP send failed, falling back to Brevo: {smtp_error}")
            return _send_email_via_brevo(
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                subject=subject,
                body=body,
                is_html=is_html,
                sender_email=sender_email,
                sender_name=sender_name,
                brevo_api_key=brevo_api_key,
            )
        return False, f"Failed to send email: {str(smtp_error)}"

@router.post("/send", response_model=SendEmailResponse)
def send_email(req: SendEmailRequest):
    """Actually send an email using SMTP"""
    try:
        html_detected = "<html" in req.body.lower() and "</html>" in req.body.lower()
        is_html = req.is_html if req.is_html is not None else html_detected
        success, message = send_email_via_smtp(
            recipient_email=req.recipient_email,
            recipient_name=req.recipient_name,
            subject=req.subject,
            body=req.body,
            is_html=is_html,
        )
        return {
            "success": success,
            "message": message,
            "recipient_email": req.recipient_email,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email error: {str(e)}")


# ── Combined generate + send endpoints (for n8n workflow) ─────────────────────

class BrevoSendRequest(BaseModel):
    """Request model for sending email via Brevo.
    Accepts brevo_api_key and sender_email so n8n can pass its own credentials."""
    candidate_email: Optional[str] = None
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    brevo_api_key: Optional[str] = None
    sender_email: Optional[str] = None
    sender_name: Optional[str] = "HR Recruitment Team"
    # For generic send-brevo
    subject: Optional[str] = None
    body: Optional[str] = None


@router.post("/send-shortlist")
def send_shortlist_email(req: BrevoSendRequest):
    """Generate the resume-shortlisted email AND send it via Brevo in one call.

    n8n should call this instead of two separate nodes (generate + Brevo HTTP).
    Pass brevo_api_key and sender_email in the request body.
    """
    candidate_email = _normalize_email(
        req.candidate_email, req.email
    )
    candidate_name = _normalize_name(
        req.candidate_name, req.name
    )

    if not candidate_email or not candidate_name:
        return {
            "success": False,
            "message": "Skipped – no candidate data",
            "skipped": True,
            "recipient_email": "none",
            "recipient_name": "none",
        }

    # 1. Generate the email content using the existing template function
    email_req = EmailRequest(
        candidate_email=candidate_email,
        candidate_name=candidate_name,
    )
    template = get_resume_shortlisted_email(email_req)
    if template.get("skipped"):
        return {
            "success": False,
            "message": "Skipped – template returned skip",
            "skipped": True,
            "recipient_email": "none",
            "recipient_name": "none",
        }

    # 2. Resolve Brevo credentials (request > env > secrets.toml)
    brevo_api_key = (
        req.brevo_api_key
        or os.getenv("BREVO_API_KEY")
        or get_smtp_config().get("brevo_api_key", "")
    )
    sender_email = (
        req.sender_email
        or os.getenv("BREVO_SENDER_EMAIL")
        or get_smtp_config().get("sender_email", "")
    )
    sender_name = req.sender_name or "HR Recruitment Team"

    # Reject placeholder key
    if not brevo_api_key or brevo_api_key == "your-real-brevo-api-key-here":
        return {
            "success": False,
            "message": "Brevo API key is not configured. Update secrets.toml or pass brevo_api_key in the request.",
            "recipient_email": candidate_email,
            "recipient_name": candidate_name,
        }

    if not sender_email:
        return {
            "success": False,
            "message": "Sender email is not configured. Set BREVO_SENDER_EMAIL env var or pass sender_email in the request.",
            "recipient_email": candidate_email,
            "recipient_name": candidate_name,
        }

    # 3. Send via Brevo with correct payload format
    print(f"📧 Sending shortlist email to {candidate_email} via Brevo...")
    success, message = _send_email_via_brevo(
        recipient_email=template["recipient_email"],
        recipient_name=template.get("recipient_name", candidate_name),
        subject=template["subject"],
        body=template["body"],
        is_html=True,
        sender_email=sender_email,
        sender_name=sender_name,
        brevo_api_key=brevo_api_key,
    )

    if success:
        print(f"✅ Shortlist email sent to {candidate_email}")
    else:
        print(f"❌ Shortlist email failed for {candidate_email}: {message}")

    return {
        "success": success,
        "message": message,
        "recipient_email": template["recipient_email"],
        "recipient_name": template.get("recipient_name", candidate_name),
        "subject": template["subject"],
    }


@router.post("/send-brevo")
def send_via_brevo(req: BrevoSendRequest):
    """Send any pre-built email via Brevo.

    n8n can call this after generating email content from another endpoint.
    Pass brevo_api_key, sender_email, subject, body, recipient info.
    """
    candidate_email = _normalize_email(req.candidate_email, req.email)
    candidate_name = _normalize_name(req.candidate_name, req.name)

    if not candidate_email or not req.subject or not req.body:
        return {
            "success": False,
            "message": "Missing required fields: candidate_email, subject, body",
            "recipient_email": candidate_email or "none",
        }

    brevo_api_key = (
        req.brevo_api_key
        or os.getenv("BREVO_API_KEY")
        or get_smtp_config().get("brevo_api_key", "")
    )
    sender_email = (
        req.sender_email
        or os.getenv("BREVO_SENDER_EMAIL")
        or get_smtp_config().get("sender_email", "")
    )
    sender_name = req.sender_name or "HR Recruitment Team"

    if not brevo_api_key or brevo_api_key == "your-real-brevo-api-key-here":
        return {
            "success": False,
            "message": "Brevo API key is not configured.",
            "recipient_email": candidate_email,
        }

    if not sender_email:
        return {
            "success": False,
            "message": "Sender email is not configured.",
            "recipient_email": candidate_email,
        }

    is_html = "<html" in req.body.lower()

    print(f"📧 Sending email to {candidate_email} via Brevo...")
    success, message = _send_email_via_brevo(
        recipient_email=candidate_email,
        recipient_name=candidate_name,
        subject=req.subject,
        body=req.body,
        is_html=is_html,
        sender_email=sender_email,
        sender_name=sender_name,
        brevo_api_key=brevo_api_key,
    )

    return {
        "success": success,
        "message": message,
        "recipient_email": candidate_email,
    }

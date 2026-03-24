from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Tuple
from datetime import datetime
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
        # Preserve original text if parsing fails.
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
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()

    oa_link = (
        req.oa_link
        or os.getenv("OFFICIAL_OA_LINK")
        or os.getenv("DEFAULT_OA_LINK")
        or "https://hackerrank.com/sample-test"
    )
    tracked_oa_link = _build_oa_launch_link(oa_link, req.candidate_email, req.candidate_name)
    
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
                <p>Dear <strong>{req.candidate_name}</strong>,</p>
                
                <p>We are pleased to inform you that your resume has been <strong>shortlisted</strong> for further consideration.</p>
                
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
        "subject": "🎉 Your Resume Has Been Shortlisted!",
        "body": html_body,
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name
    }

@router.post("/oa-shortlisted", response_model=EmailResponse)
def get_oa_shortlisted_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()
    return {
        "subject": "Congratulations! You are Shortlisted",
        "body": "Dear Candidate,\n\nWe are pleased to inform you that you have been shortlisted for the next round.\n\nBest,\nRecruiting Team",
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name
    }

@router.post("/interview-confirm", response_model=EmailResponse)
def get_interview_confirm_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()
    return {
        "subject": "Interview Confirmation",
        "body": "Dear Candidate,\n\nYour interview has been confirmed. Please check the details in your calendar invitation.\n\nBest,\nRecruiting Team",
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name
    }

@router.post("/interview-reminder", response_model=EmailResponse)
def get_interview_reminder_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
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
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name
    }

@router.post("/interview-invite", response_model=EmailResponse)
def get_interview_invite_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()

    round_number = req.round_number or 1
    round_label = req.round_label or "Interview"
    interview_format = req.interview_format or "video call"
    scheduled_time = _format_scheduled_time_for_email(req.scheduled_time, req.timezone)
    if req.feedback_form_url:
        base_feedback_url = req.feedback_form_url
    else:
        public_base = (os.getenv("PUBLIC_API_BASE_URL") or "http://localhost:8000").rstrip("/")
        base_feedback_url = f"{public_base}/feedback-form.html"

    feedback_query = {}
    if req.interview_id is not None:
        feedback_query["interview_id"] = req.interview_id
    if req.candidate_name:
        feedback_query["candidate"] = req.candidate_name
    if req.candidate_email:
        feedback_query["candidate_email"] = req.candidate_email
    if round_label:
        feedback_query["job"] = round_label

    feedback_form_url = (
        f"{base_feedback_url}?{urlencode(feedback_query)}"
        if feedback_query
        else base_feedback_url
    )

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
      <div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:30px;border-radius:10px 10px 0 0;text-align:center;">
        <h1>You're Invited to Interview!</h1>
        <p style="font-size:18px;opacity:0.9;">Round {round_number}: {round_label}</p>
      </div>
      <div style="background:#f9fafb;padding:30px;border-radius:0 0 10px 10px;">
        <p>Dear <strong>{req.candidate_name}</strong>,</p>
        <p>We are pleased to invite you to <strong>Round {round_number} – {round_label}</strong> of
           our interview process!</p>

        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr style="background:#edf2f7;">
            <td style="padding:8px 12px;font-weight:bold;">Format</td>
            <td style="padding:8px 12px;">{interview_format.title()}</td>
          </tr>
          <tr>
            <td style="padding:8px 12px;font-weight:bold;">Confirmed Time</td>
            <td style="padding:8px 12px;">{scheduled_time}</td>
          </tr>
          <tr style="background:#edf2f7;">
            <td style="padding:8px 12px;font-weight:bold;">Duration</td>
            <td style="padding:8px 12px;">~60 minutes</td>
          </tr>
        </table>

        {slots_html}
        {meeting_section}

                <div style="margin:18px 0;padding:14px;background:#eef2ff;border-left:4px solid #4f46e5;border-radius:6px;">
                    <strong>Interviewer Scorecard:</strong>
                    Please submit interview feedback after the session.
                    <br><br>
                    <a href="{feedback_form_url}" style="display:inline-block;padding:10px 16px;background:#4f46e5;color:white;text-decoration:none;border-radius:6px;font-weight:bold;">
                        Submit Feedback Scorecard
                    </a>
                </div>

        <h3 style="color:#4a5568;">What to Expect</h3>
        <ul>
          <li>Discussion of your background and relevant experience</li>
          <li>Technical / competency-based questions aligned to the role</li>
          <li>A chance for you to ask questions about the team and company</li>
        </ul>

        <div style="background:#ebf8ff;border-left:4px solid #4299e1;padding:12px;margin:16px 0;border-radius:4px;">
          <strong>Need to reschedule?</strong> Please reply to this email at least 24 hours in advance
          and we will do our best to accommodate you.
        </div>

                <div style="margin:20px 0;padding:16px;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;text-align:center;">
                    <p style="margin:0 0 10px 0;"><strong>Post-Interview Action</strong></p>
                    <p style="margin:0 0 14px 0;">After the interview, please submit the feedback scorecard.</p>
                    <a href="{feedback_form_url}" style="display:inline-block;padding:12px 20px;background:#059669;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:bold;">
                        Submit Feedback
                    </a>
                    <p style="margin:12px 0 0 0;font-size:12px;color:#4b5563;">
                        If the button does not open, use this link: <a href="{feedback_form_url}">{feedback_form_url}</a>
                    </p>
                </div>

        <p>We look forward to speaking with you!</p>
        <br><p>Best regards,<br><strong>HR Recruiting Team</strong></p>
      </div>
      <p style="text-align:center;font-size:12px;color:#888;margin-top:20px;">
        This is an automated email from our recruitment system.
      </p>
    </div>
    </body></html>
    """

    return {
        "subject": f"Interview Invitation – Round {round_number}: {round_label}",
        "body": html_body,
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name,
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
            <td style="padding:8px 12px;">{req.candidate_name} ({req.candidate_email})</td>
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
        "subject": f"Interview Kit: {req.candidate_name} – {req.round_label}",
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
    next_round_number: int = 2
    next_round_label: str = "Technical Round"

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
        f'<p><a href="{req.offer_link}" style="display:inline-block;padding:14px 30px;'
        f'background:#667eea;color:white;border-radius:5px;text-decoration:none;font-weight:bold;">'
        f'Review &amp; Sign Offer Letter</a></p>'
        if req.offer_link
        else "<p>Our team will send you the formal offer letter document within 1–2 business days.</p>"
    )

    html_body = f"""
    <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
    <div style="max-width:600px;margin:auto;padding:20px;">
      <div style="background:linear-gradient(135deg,#ed8936,#c05621);color:white;padding:30px;
                  border-radius:10px 10px 0 0;text-align:center;">
        <h1>🌟 Offer Letter</h1>
      </div>
      <div style="background:#f9fafb;padding:30px;border-radius:0 0 10px 10px;">
        <p>Dear <strong>{req.candidate_name}</strong>,</p>
        <p>We are thrilled to extend a formal offer of employment for the role of
           <strong>{req.role}</strong>. After a thorough process you have truly stood out
           and we are excited about the prospect of you joining our team.</p>
        <p>Please review the offer letter and sign electronically at your earliest convenience
           (we kindly ask for a response within <strong>5 business days</strong>).</p>
        {sign_section}
        <p>If you have any questions about the offer, compensation, or start date, please
           don't hesitate to reply to this email.</p>
        <p>We look forward to welcoming you aboard!</p>
        <br><p>Warm regards,<br><strong>HR Recruiting Team</strong></p>
      </div>
    </div>
    </body></html>
    """

    return {
        "subject": f"🌟 Your Offer Letter – {req.role}",
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
        return False, f"Brevo send failed ({response.status_code}): {response.text[:300]}"
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
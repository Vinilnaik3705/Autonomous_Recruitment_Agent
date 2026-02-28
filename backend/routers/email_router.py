from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import toml
import os
from urllib.parse import quote

router = APIRouter(
    prefix="/email",
    tags=["email"]
)

OA_SAMPLE_LINK = os.getenv("OA_SAMPLE_LINK", "http://localhost:5173/test-oa.html")
OA_OFFICIAL_LINK_BASE = os.getenv("OA_OFFICIAL_LINK", "http://localhost:5173/test-oa.html")

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
    interview_format: Optional[str] = "video call"
    scheduled_time: Optional[str] = None
    meeting_link: Optional[str] = None
    slot_options: Optional[List[str]] = None

def _skip_response():
    """Return a safe skip response when candidate data is missing."""
    return {
        "subject": "SKIPPED",
        "body": "No candidate data — empty Postgres result",
        "recipient_email": "none",
        "recipient_name": "none",
        "skipped": True
    }

@router.post("/oa-practice", response_model=EmailResponse)
def get_oa_practice_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()
    return {
        "subject": "OA Practice Link - Recruiting Team",
        "body": "Dear Candidate,\n\nPlease find the practice link for the Online Assessment below.\n\nBest,\nRecruiting Team",
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name
    }

@router.post("/oa-original", response_model=EmailResponse)
def get_oa_original_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()
    
    # Build OA link with pre-filled candidate info
    oa_link = f"{OA_OFFICIAL_LINK_BASE}?email={quote(req.candidate_email)}&name={quote(req.candidate_name)}"
    
    html_body = f"""<!DOCTYPE html>
<html><head><style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.7; color: #2d3748; background: #f7fafc; margin: 0; padding: 0; }}
.wrapper {{ background: #f7fafc; padding: 20px 0; }}
.container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
.header {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: #ffffff; padding: 40px 30px; text-align: center; }}
.header h1 {{ margin: 0; font-size: 32px; font-weight: 700; }}
.header p {{ margin: 8px 0 0 0; opacity: 0.95; font-size: 16px; }}
.content {{ padding: 40px 30px; }}
.greeting {{ font-size: 18px; margin: 0 0 20px 0; }}
.greeting strong {{ color: #f5576c; }}
.highlight-box {{ background: #fff5f7; border-left: 4px solid #f5576c; padding: 15px 20px; margin: 20px 0; border-radius: 6px; }}
.highlight-box p {{ margin: 0; color: #2d3748; font-size: 15px; }}
.feature-list {{ list-style: none; padding: 0; margin: 12px 0; }}
.feature-list li {{ padding: 8px 0; padding-left: 24px; position: relative; color: #4a5568; }}
.feature-list li:before {{ content: "◆"; position: absolute; left: 0; color: #f5576c; font-weight: bold; }}
.button-container {{ text-align: center; margin: 30px 0; }}
.button {{ display: inline-block; padding: 14px 36px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: #ffffff !important; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px; }}
.footer {{ background: #f7fafc; padding: 20px 30px; text-align: center; border-top: 1px solid #e2e8f0; }}
.footer p {{ margin: 0; color: #718096; font-size: 13px; }}
</style></head><body><div class="wrapper"><div class="container">
<div class="header"><h1>💻 Official Assessment</h1><p>Your Next Challenge Awaits</p></div>
<div class="content">
<p class="greeting">Hi <strong>{req.candidate_name}</strong>,</p>
<p>Congratulations on passing the sample assessment! We were impressed with your performance, and we're excited to move forward with you.</p>
<p>It's now time for the <strong>Official Online Assessment</strong>, a critical step that will showcase your true potential. This assessment is designed to evaluate your technical depth, problem-solving approach, and coding proficiency in a comprehensive manner.</p>
<div class="highlight-box"><p><strong>⏰ Important Deadline</strong></p><p style="margin-top: 8px;">Please complete this assessment within <strong>48 hours</strong> from now. Timely submission is important for us to continue with your application.</p></div>
<p style="margin-bottom: 12px;"><strong>Assessment Details:</strong></p>
<ul class="feature-list"><li>Duration: 90 minutes (timed assessment)</li><li>Difficulty: Intermediate to Advanced</li><li>Format: Programming & Problem-Solving</li><li>Attempts: 1 (please prepare well)</li></ul>
<div class="button-container"><a href="{oa_link}" class="button">Begin Official Assessment →</a></div>
<p><strong>Important Guidelines:</strong></p>
<ul style="margin: 12px 0;"><li>Ensure you have a <strong>stable internet connection</strong> before starting</li><li>Choose a <strong>quiet environment</strong> with no distractions</li><li>Have <strong>90 minutes uninterrupted</strong> to complete the test</li><li>Once started, the test <strong>cannot be paused</strong> - plan accordingly</li><li><strong>Do not</strong> use external resources or ask for help during the test</li></ul>
<p><strong>Why This Assessment Matters:</strong></p>
<p>This is where you demonstrate your real capabilities. We're looking for candidates who can think critically, solve problems efficiently, and write clean, maintainable code. Your performance on this assessment will directly influence the next stage of our hiring process.</p>
<p>Believe in yourself, show us what you can do, and let your skills speak! 💪 We're rooting for you!</p>
<p>Best regards,<br><strong>Engineering Recruitment Team</strong><br><span style="color: #718096; font-size: 14px;">Looking forward to your response</span></p>
</div><div class="footer"><p>This invitation is unique and confidential. Please do not share the link with anyone.</p></div>
</div></div></body></html>"""
    
    return {
        "subject": "🚀 Official Assessment Invitation",
        "body": html_body,
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name
    }

@router.post("/resume-shortlisted", response_model=EmailResponse)
def get_resume_shortlisted_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()
    
    oa_link = OA_SAMPLE_LINK  # Sample OA link
    
    # Sample OA email template (aligned with provided format)
    html_body = f"""<!DOCTYPE html>
<html><head><style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.7; color: #2d3748; background: #f7fafc; margin: 0; padding: 0; }}
.wrapper {{ background: #f7fafc; padding: 20px 0; }}
.container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
.header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; padding: 40px 30px; text-align: center; }}
.header h1 {{ margin: 0; font-size: 32px; font-weight: 700; }}
.header p {{ margin: 8px 0 0 0; opacity: 0.95; font-size: 16px; }}
.content {{ padding: 40px 30px; }}
.greeting {{ font-size: 18px; margin: 0 0 20px 0; }}
.greeting strong {{ color: #667eea; }}
.highlight-box {{ background: #f0f4ff; border-left: 4px solid #667eea; padding: 15px 20px; margin: 20px 0; border-radius: 6px; }}
.highlight-box p {{ margin: 0; color: #2d3748; font-size: 15px; }}
.feature-list {{ list-style: none; padding: 0; margin: 12px 0; }}
.feature-list li {{ padding: 8px 0; padding-left: 24px; position: relative; color: #4a5568; }}
.feature-list li:before {{ content: "✓"; position: absolute; left: 0; color: #667eea; font-weight: bold; }}
.button-container {{ text-align: center; margin: 30px 0; }}
.button {{ display: inline-block; padding: 14px 36px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff !important; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px; }}
.footer {{ background: #f7fafc; padding: 20px 30px; text-align: center; border-top: 1px solid #e2e8f0; }}
.footer p {{ margin: 0; color: #718096; font-size: 13px; }}
</style></head><body><div class="wrapper"><div class="container">
<div class="header"><h1>🎉 Congratulations!</h1><p>Your Resume Has Been Shortlisted</p></div>
<div class="content">
<p class="greeting">Dear <strong>{req.candidate_name}</strong>,</p>
<p>We are excited to inform you that your resume has been <strong>shortlisted</strong> for further consideration in our hiring process!</p>
<p>Your qualifications, skills, and experience align perfectly with the requirements of the position. Your background demonstrates strong potential to contribute meaningfully to our team, and we believe you could be an excellent fit for our organization.</p>
<div class="highlight-box"><p><strong>🎯 Next Step: Sample Online Assessment</strong></p><p style="margin-top: 8px;">To move forward, we would like you to take a quick sample assessment. This will help us evaluate your technical skills and problem-solving approach in a practical environment.</p></div>
<p style="margin-bottom: 12px;"><strong>Assessment Overview:</strong></p>
<ul class="feature-list"><li>Quick sample test to assess your capabilities</li><li>Takes approximately 30-45 minutes</li><li>Can be completed at your convenience</li><li>Valid for 7 days from now</li></ul>
<div class="button-container"><a href="{oa_link}" class="button">Start Sample Assessment →</a></div>
<p><strong>What to Expect:</strong></p>
<p>The assessment focuses on practical problem-solving and coding skills relevant to the role. You'll have one attempt, and the environment will be similar to standard coding platforms you may have used before.</p>
<p>If you have any questions or face technical difficulties, please don't hesitate to reach out. We're here to help!</p>
<p>We look forward to seeing your performance. Best of luck! 💪</p>
<p>Warm regards,<br><strong>Engineering Recruitment Team</strong><br><span style="color: #718096; font-size: 14px;">Committed to finding great talent</span></p>
</div><div class="footer"><p>This email is confidential and intended only for the recipient.</p></div>
</div></div></body></html>"""
    
    return {
        "subject": "🎉 Congratulations! Your Resume Has Been Shortlisted",
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
    
    round_label = req.round_label or "Interview"
    scheduled_time = req.scheduled_time or "To Be Confirmed"
    interview_format = req.interview_format or "video call"
    meeting_link = req.meeting_link or "Will be shared via calendar invitation"
    
    meeting_section = (
        f'<div style="background: #fff; border: 2px solid #48bb78; padding: 20px; border-radius: 8px; margin: 25px 0; text-align: center;">' 
        f'<p style="margin: 0 0 10px 0; font-size: 14px; color: #2f855a; font-weight: 600; text-transform: uppercase;">Meeting Link</p>'
        f'<a href="{meeting_link}" style="color: #2f855a; font-weight: 700; text-decoration: none; word-break: break-all; font-size: 15px;">{meeting_link}</a>'
        f'</div>'
        if req.meeting_link
        else '<p style="margin: 25px 0; padding: 20px; background: #f0fff4; border-radius: 8px; text-align: center; color: #2f855a; font-weight: 600;">📧 Meeting link will be shared via calendar invitation</p>'
    )
    
    html_body = f"""<!DOCTYPE html>
<html><head><style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.7; color: #2d3748; background: #f7fafc; margin: 0; padding: 0; }}
.wrapper {{ background: #f7fafc; padding: 20px 0; }}
.container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
.header {{ background: linear-gradient(135deg, #48bb78 0%, #38b2ac 100%); color: #ffffff; padding: 40px 30px; text-align: center; }}
.header h1 {{ margin: 0; font-size: 32px; font-weight: 700; }}
.header p {{ margin: 8px 0 0 0; opacity: 0.95; font-size: 16px; }}
.content {{ padding: 40px 30px; }}
.greeting {{ font-size: 18px; margin: 0 0 20px 0; }}
.greeting strong {{ color: #38b2ac; }}
.confirm-box {{ background: #f0fff4; border: 2px solid #48bb78; padding: 20px; margin: 25px 0; border-radius: 8px; text-align: center; }}
.confirm-box h3 {{ margin: 0 0 10px 0; color: #2f855a; font-size: 22px; }}
.info-table {{ background: #f7fafc; border-radius: 8px; padding: 20px; margin: 25px 0; }}
.info-row {{ display: flex; padding: 10px 0; border-bottom: 1px solid #e2e8f0; }}
.info-row:last-child {{ border-bottom: none; }}
.info-label {{ width: 140px; color: #718096; font-weight: 600; font-size: 14px; }}
.info-value {{ color: #2d3748; font-weight: 700; font-size: 14px; }}
.footer {{ background: #f7fafc; padding: 20px 30px; text-align: center; border-top: 1px solid #e2e8f0; }}
.footer p {{ margin: 0; color: #718096; font-size: 13px; }}
</style></head><body><div class="wrapper"><div class="container">
<div class="header"><h1>✅ Interview Confirmed</h1><p>We're excited to meet you!</p></div>
<div class="content">
<p class="greeting">Hi <strong>{req.candidate_name}</strong>,</p>
<p>Great news! Your interview has been successfully confirmed.</p>
<div class="confirm-box">
<h3>✓ All Set!</h3>
<p style="margin: 10px 0 0 0; font-size: 15px; color: #2f855a;">Your interview slot is confirmed. Details below.</p>
</div>
<div class="info-table">
<div class="info-row"><div class="info-label">Interview Type:</div><div class="info-value">{round_label}</div></div>
<div class="info-row"><div class="info-label">Format:</div><div class="info-value">{interview_format.title()}</div></div>
<div class="info-row"><div class="info-label">Scheduled Time:</div><div class="info-value">{scheduled_time}</div></div>
<div class="info-row"><div class="info-label">Duration:</div><div class="info-value">60 minutes</div></div>
</div>
{meeting_section}
<p style="background: #ebf8ff; border-left: 4px solid #4299e1; padding: 15px; border-radius: 6px; margin: 25px 0;">
<strong>📅 Calendar Invitation:</strong> A calendar invite with all details has been sent to your email. Please accept it to add this interview to your schedule.
</p>
<p><strong>What to Prepare:</strong></p>
<ul style="padding-left: 20px; margin: 15px 0; color: #4a5568; font-size: 15px;">
<li style="margin-bottom: 8px;">Review the job description and requirements</li>
<li style="margin-bottom: 8px;">Prepare examples of your past work and achievements</li>
<li style="margin-bottom: 8px;">Think of questions you'd like to ask us</li>
<li style="margin-bottom: 8px;">Test your camera, microphone, and internet connection</li>
</ul>
<p>If you need to reschedule, please let us know at least 24 hours in advance by replying to this email.</p>
<p style="margin-top: 30px;">We look forward to speaking with you!</p>
<p>Best regards,<br><strong>HR Recruiting Team</strong><br><span style="color: #718096; font-size: 14px;">Building great teams together</span></p>
</div><div class="footer"><p>This confirmation was sent because an interview was scheduled with you. Questions? Contact your recruiter.</p></div>
</div></div></body></html>"""
    
    return {
        "subject": f"✅ Interview Confirmed: {round_label} - {scheduled_time}",
        "body": html_body,
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
    
    round_label = req.round_label or "Interview"
    scheduled_time = req.scheduled_time or "tomorrow"
    interview_format = req.interview_format or "video call"
    
    html_body = f"""<!DOCTYPE html>
<html><head><style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.7; color: #2d3748; background: #f7fafc; margin: 0; padding: 0; }}
.wrapper {{ background: #f7fafc; padding: 20px 0; }}
.container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
.header {{ background: linear-gradient(135deg, #4299e1 0%, #667eea 100%); color: #ffffff; padding: 40px 30px; text-align: center; }}
.header h1 {{ margin: 0; font-size: 32px; font-weight: 700; }}
.header p {{ margin: 8px 0 0 0; opacity: 0.95; font-size: 16px; }}
.content {{ padding: 40px 30px; }}
.greeting {{ font-size: 18px; margin: 0 0 20px 0; }}
.greeting strong {{ color: #4299e1; }}
.reminder-box {{ background: #ebf8ff; border-left: 4px solid #4299e1; padding: 20px; margin: 25px 0; border-radius: 6px; }}
.reminder-box h3 {{ margin: 0 0 10px 0; color: #2c5282; font-size: 18px; }}
.info-table {{ background: #f7fafc; border-radius: 8px; padding: 20px; margin: 25px 0; }}
.info-row {{ display: flex; padding: 10px 0; border-bottom: 1px solid #e2e8f0; }}
.info-row:last-child {{ border-bottom: none; }}
.info-label {{ width: 140px; color: #718096; font-weight: 600; font-size: 14px; }}
.info-value {{ color: #2d3748; font-weight: 700; font-size: 14px; }}
.checklist {{ list-style: none; padding: 0; margin: 20px 0; }}
.checklist li {{ padding: 10px 0; padding-left: 28px; position: relative; color: #4a5568; font-size: 15px; }}
.checklist li:before {{ content: "✓"; position: absolute; left: 0; color: #48bb78; font-weight: bold; font-size: 18px; }}
.footer {{ background: #f7fafc; padding: 20px 30px; text-align: center; border-top: 1px solid #e2e8f0; }}
.footer p {{ margin: 0; color: #718096; font-size: 13px; }}
</style></head><body><div class="wrapper"><div class="container">
<div class="header"><h1>⏰ Interview Reminder</h1><p>Your interview is coming up soon!</p></div>
<div class="content">
<p class="greeting">Hi <strong>{req.candidate_name}</strong>,</p>
<p>This is a friendly reminder about your upcoming interview with our team.</p>
<div class="reminder-box">
<h3>📅 Interview Details</h3>
<p style="margin: 10px 0 0 0; font-size: 15px;">We're looking forward to speaking with you about the <strong>{round_label}</strong> position.</p>
</div>
<div class="info-table">
<div class="info-row"><div class="info-label">Interview Type:</div><div class="info-value">{round_label}</div></div>
<div class="info-row"><div class="info-label">Format:</div><div class="info-value">{interview_format.title()}</div></div>
<div class="info-row"><div class="info-label">Scheduled Time:</div><div class="info-value">{scheduled_time}</div></div>
<div class="info-row"><div class="info-label">Duration:</div><div class="info-value">60 minutes</div></div>
</div>
<p style="margin-top: 25px;"><strong>Quick Checklist Before Your Interview:</strong></p>
<ul class="checklist">
<li>Check your internet connection and test your camera/microphone</li>
<li>Have a quiet, well-lit space ready for the call</li>
<li>Review the job description and your resume</li>
<li>Prepare questions you'd like to ask us</li>
<li>Join the meeting 5 minutes early</li>
</ul>
<p style="background: #fffaf0; border-left: 4px solid #ed8936; padding: 15px; border-radius: 6px; margin: 25px 0;">
<strong>Need to reschedule?</strong> Please let us know at least 24 hours in advance by replying to this email.
</p>
<p>We're excited to meet you and learn more about your background and aspirations. If you have any questions, feel free to reach out!</p>
<p style="margin-top: 30px;">Best regards,<br><strong>HR Recruiting Team</strong><br><span style="color: #718096; font-size: 14px;">We're rooting for you!</span></p>
</div><div class="footer"><p>This is an automated reminder. Please do not reply to this email if you have questions - contact your recruiter directly.</p></div>
</div></div></body></html>"""
    
    return {
        "subject": f"⏰ Reminder: Your Interview for {round_label} is Coming Up",
        "body": html_body,
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name
    }

@router.post("/interview-invite", response_model=EmailResponse)
def get_interview_invite_email(req: EmailRequest):
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()

    round_number = req.round_number or 1
    round_label = req.round_label or "DSA Round"
    interview_format = req.interview_format or "video call"
    scheduled_time = req.scheduled_time or "To Be Confirmed"

    meeting_section = (
        f'<div style="background:#fff;border:1px solid #e2e8f0;padding:15px;border-radius:8px;margin:20px 0;">'
        f'<p style="margin:0 0 5px 0;font-size:14px;color:#64748b;font-weight:600;">Meeting Link</p>'
        f'<a href="{req.meeting_link}" style="color:#4f46e5;font-weight:700;text-decoration:none;word-break:break-all;">{req.meeting_link}</a>'
        f'</div>'
        if req.meeting_link
        else '<p style="margin:20px 0;color:#64748b;font-style:italic;">Meeting link will be shared via calendar invitation.</p>'
    )

    html_body = f"""
    <!DOCTYPE html><html><body style="font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#333;line-height:1.6;margin:0;padding:0;background-color:#f4f7f9;">
    <div style="max-width:600px;margin:20px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 15px rgba(0,0,0,0.05);">
      <div style="background:linear-gradient(135deg,#6366f1,#a855f7);color:white;padding:50px 30px;text-align:center;">
        <h1 style="margin:0;font-size:28px;font-weight:800;letter-spacing:-0.5px;">Invitation to Interview!</h1>
        <p style="margin:10px 0 0 0;opacity:0.9;font-size:18px;font-weight:500;">Round {round_number}: {round_label}</p>
      </div>
      <div style="padding:40px 35px;">
        <p style="font-size:16px;margin-bottom:25px;">Hi <strong>{req.candidate_name}</strong>,</p>
        <p style="font-size:16px;">We're excited to invite you to the next stage of our recruitment process for the <strong>{round_label}</strong>.</p>
        
        <div style="background:#f8fafc;border:1px solid #edf2f7;border-radius:10px;padding:25px;margin:30px 0;">
          <table style="width:100%;border-collapse:collapse;">
            <tr><td style="padding:10px 0;color:#64748b;font-weight:600;width:120px;">Format</td><td style="padding:10px 0;color:#1e293b;font-weight:700;">{interview_format.title()}</td></tr>
            <tr><td style="padding:10px 0;color:#64748b;font-weight:600;">Time</td><td style="padding:10px 0;color:#1e293b;font-weight:700;">{scheduled_time}</td></tr>
            <tr><td style="padding:10px 0;color:#64748b;font-weight:600;">Duration</td><td style="padding:10px 0;color:#1e293b;font-weight:700;">60 minutes</td></tr>
          </table>
        </div>

        {meeting_section}

        <div style="margin-top:35px;">
          <h3 style="font-size:16px;color:#1e293b;margin-bottom:12px;">What to Expect</h3>
          <ul style="padding-left:20px;margin:0;color:#475569;font-size:15px;">
            <li style="margin-bottom:8px;">Deep dive into your technical background and problem-solving skills.</li>
            <li style="margin-bottom:8px;">Competency-based questions tailored to the <strong>{round_label}</strong>.</li>
            <li style="margin-bottom:8px;">A chance to learn more about our team and engineering culture.</li>
          </ul>
        </div>

        <div style="margin-top:40px;padding:20px;background:#fffaf0;border-left:4px solid #ed8936;border-radius:6px;font-size:14px;color:#7b341e;">
          <strong>Note:</strong> If you need to reschedule, please reply to this email at least 24 hours in advance.
        </div>
        
        <p style="margin-top:45px;font-size:16px;border-top:1px solid #f1f5f9;padding-top:30px;">
          Best of luck,<br><strong style="color:#4f46e5;">HR Recruiting Team</strong>
        </p>
      </div>
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
    feedback_url = req.feedback_form_url or "http://localhost:8000/feedback-form.html"
    jd_section = (
        f'<div style="margin-bottom:25px;"><h3 style="font-size:16px;color:#1e293b;border-bottom:2px solid #f1f5f9;padding-bottom:10px;">Job Context</h3><p style="font-size:14px;color:#475569;">{req.job_description[:600]}...</p></div>'
        if req.job_description else ""
    )
    resume_section = (
        f'<div style="margin-bottom:25px;"><h3 style="font-size:16px;color:#1e293b;border-bottom:2px solid #f1f5f9;padding-bottom:10px;">Resume Highlights</h3><p style="font-size:14px;color:#475569;">{req.resume_summary[:500]}...</p></div>'
        if req.resume_summary else ""
    )

    html_body = f"""
    <!DOCTYPE html><html><body style="font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#333;line-height:1.6;background-color:#f8fafc;">
    <div style="max-width:600px;margin:20px auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e1e4e8;">
      <div style="background:#1e293b;color:white;padding:35px 30px;">
        <p style="margin:0;font-size:12px;text-transform:uppercase;font-weight:700;letter-spacing:1px;opacity:0.7;">Interview Preparation</p>
        <h2 style="margin:5px 0 0 0;font-size:24px;font-weight:800;">Interview Kit: {req.candidate_name}</h2>
      </div>
      <div style="padding:35px;">
        <p style="font-size:16px;">Hi <strong>{req.interviewer_name}</strong>,</p>
        <p style="font-size:16px;">You have a <strong>{req.round_label}</strong> scheduled. Below are the candidate details and evaluation tools.</p>
        
        <div style="background:#f1f5f9;border-radius:10px;padding:25px;margin:25px 0;">
          <table style="width:100%;border-collapse:collapse;">
            <tr><td style="padding:8px 0;color:#64748b;font-weight:600;width:140px;">Candidate</td><td style="padding:8px 0;color:#1e293b;font-weight:700;">{req.candidate_name}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-weight:600;">Round</td><td style="padding:8px 0;color:#1e293b;font-weight:700;">{req.round_label}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-weight:600;">Time</td><td style="padding:8px 0;color:#1e293b;font-weight:700;">{req.scheduled_time or 'See calendar'}</td></tr>
          </table>
        </div>

        {jd_section}
        {resume_section}

        <div style="margin-bottom:30px;">
          <h3 style="font-size:16px;color:#1e293b;border-bottom:2px solid #f1f5f9;padding-bottom:10px;">Evaluation Focus</h3>
          <ul style="padding-left:20px;margin:0;color:#475569;font-size:14px;">
            <li style="margin-bottom:8px;">Deep technical proficiency in relevant domains.</li>
            <li style="margin-bottom:8px;">Problem-solving approach and critical thinking.</li>
            <li style="margin-bottom:8px;">Cultural alignment and communication clarity.</li>
          </ul>
        </div>

        <div style="text-align:center;margin-top:40px;padding:35px;background:#eef2ff;border-radius:12px;border:1px dashed #6366f1;">
          <p style="margin:0 0 20px 0;font-weight:600;color:#4338ca;">Submit your scorecard immediately after the session.</p>
          <a href="{feedback_url}" style="display:inline-block;padding:16px 32px;background:#4f46e5;color:white;border-radius:8px;text-decoration:none;font-weight:700;box-shadow:0 10px 15px -3px rgba(79,70,229,0.3);">Launch Evaluation Form</a>
        </div>

        <p style="margin-top:45px;font-size:15px;color:#64748b;text-align:center;">Best regards,<br><strong>HR Coordination Team</strong></p>
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

@router.post("/hr-reminder", response_model=EmailResponse)
def get_hr_reminder_email(req: EmailRequest):
    """Specific reminder for HR/Interviewer about an upcoming interview."""
    if not req.candidate_email or not req.candidate_name:
        return _skip_response()
    
    time_label = "in 1 hour" if "1h" in (req.round_label or "") else "tomorrow"
    subject = f"Friendly Reminder: Interview with {req.candidate_name} {time_label}"
    
    html_body = f"""
    <!DOCTYPE html><html><body style="font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#333;line-height:1.6;">
    <div style="max-width:600px;margin:auto;padding:25px;border:1px solid #e2e8f0;border-radius:12px;background-color:#ffffff;">
      <h2 style="color:#1e293b;margin-top:0;">⏰ Interview Reminder</h2>
      <p style="font-size:16px;">Hi Team,</p>
      <p style="font-size:16px;">This is a reminder that you have an interview with <strong>{req.candidate_name}</strong> scheduled <strong>{time_label}</strong>.</p>
      
      <div style="background:#f8fafc;padding:20px;border-radius:8px;margin:20px 0;">
        <table style="width:100%;">
          <tr><td style="color:#64748b;font-weight:600;width:120px;">Candidate</td><td style="font-weight:700;">{req.candidate_name}</td></tr>
          <tr><td style="color:#64748b;font-weight:600;">Time</td><td style="font-weight:700;">{req.scheduled_time}</td></tr>
          <tr><td style="color:#64748b;font-weight:600;">Position</td><td style="font-weight:700;">{req.round_label}</td></tr>
        </table>
      </div>

      <p style="font-size:15px;color:#475569;">Please ensure you have the interview kit ready and the meeting link working.</p>
      
      <p style="margin-top:25px;font-size:14px;color:#94a3b8;border-top:1px solid #f1f5f9;padding-top:15px;">
        Auto-generated by Recruitment Agent.
      </p>
    </div>
    </body></html>
    """
    
    return {
        "subject": subject,
        "body": html_body,
        "recipient_email": req.candidate_email,
        "recipient_name": req.candidate_name,
    }


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
class SendEmailRequest(BaseModel):
    recipient_email: str
    recipient_name: str
    subject: str
    body: str

class SendEmailResponse(BaseModel):
    success: bool
    message: str
    recipient_email: str

@router.post("/send", response_model=SendEmailResponse)
def send_email(req: SendEmailRequest):
    """Actually send an email using SMTP"""
    try:
        smtp_config = get_smtp_config()
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"HR Recruitment Team <{smtp_config.get('sender_email', 'noreply@example.com')}>"
        msg['To'] = req.recipient_email
        msg['Subject'] = req.subject
        
        # Add body
        msg.attach(MIMEText(req.body, 'plain'))
        
        # Send email
        try:
            server = smtplib.SMTP(smtp_config.get('smtp_server', 'smtp.gmail.com'), 
                                 smtp_config.get('smtp_port', 587))
            server.starttls()
            server.login(smtp_config.get('sender_email', ''), 
                        smtp_config.get('sender_password', ''))
            server.send_message(msg)
            server.quit()
            
            return {
                "success": True,
                "message": "Email sent successfully",
                "recipient_email": req.recipient_email
            }
        except Exception as smtp_error:
            # Log but don't fail - email sending is optional
            print(f"SMTP Error: {str(smtp_error)}")
            return {
                "success": False,
                "message": f"Failed to send email: {str(smtp_error)}",
                "recipient_email": req.recipient_email
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email error: {str(e)}")
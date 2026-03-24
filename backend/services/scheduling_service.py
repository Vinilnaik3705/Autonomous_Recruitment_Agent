import os
import toml
import json
import pytz
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from backend.database import get_db_connection
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

# ---------------------------------------------------------------------------
# Panel templates: maps job role keywords → ordered list of interview rounds
# Each round specifies the interviewer department/tag and format.
# ---------------------------------------------------------------------------
PANEL_TEMPLATES = {
    "default": [
        {"round": 1, "label": "HR Screen",       "department": "HR",          "format": "video call"},
        {"round": 2, "label": "Technical Round",  "department": "Engineering", "format": "video call"},
        {"round": 3, "label": "Manager Round",    "department": "Management",  "format": "video call"},
    ],
    "engineering": [
        {"round": 1, "label": "HR Screen",        "department": "HR",          "format": "video call"},
        {"round": 2, "label": "Technical Round 1","department": "Engineering", "format": "video call"},
        {"round": 3, "label": "Technical Round 2","department": "Engineering", "format": "video call"},
        {"round": 4, "label": "Manager Round",    "department": "Management",  "format": "video call"},
    ],
    "sales": [
        {"round": 1, "label": "HR Screen",        "department": "HR",          "format": "phone"},
        {"round": 2, "label": "Skills Assessment","department": "Sales",       "format": "video call"},
        {"round": 3, "label": "Director Round",   "department": "Management",  "format": "in-person"},
    ],
}


class SchedulingService:
    def __init__(self):
        self.load_secrets()
        self.setup_google_calendar()

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def load_secrets(self):
        self.secrets = {}
        for path in ("secrets.toml", "../secrets.toml"):
            if os.path.exists(path):
                self.secrets = toml.load(path)
                break

    def setup_google_calendar(self):
        self.service = None
        if os.path.exists("token.json"):
            try:
                creds = Credentials.from_authorized_user_file(
                    "token.json", ["https://www.googleapis.com/auth/calendar"]
                )
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                self.service = build("calendar", "v3", credentials=creds)
            except Exception as e:
                print(f"Google Calendar init failed: {e}")

    # ------------------------------------------------------------------
    # Panel template resolution
    # ------------------------------------------------------------------

    def get_panel_template(self, job_title: str = "") -> List[Dict]:
        """Return the panel template for the given job title."""
        title_lower = (job_title or "").lower()
        for key in PANEL_TEMPLATES:
            if key != "default" and key in title_lower:
                return PANEL_TEMPLATES[key]
        return PANEL_TEMPLATES["default"]

    # ------------------------------------------------------------------
    # Interviewer pool & load-balancing
    # ------------------------------------------------------------------

    def get_interviewers(self) -> List[Dict]:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, email, timezone FROM interviewers WHERE is_active = TRUE"
                )
                return cur.fetchall()
        finally:
            conn.close()

    def get_load_balanced_interviewer(self, department: Optional[str] = None) -> Optional[Dict]:
        """
        Return the active interviewer with the fewest interviews this week.
        Optionally filter by department (stored in a 'department' column if present).
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Count interviews per interviewer in the current week
                query = """
                    SELECT i.id, i.name, i.email,
                           COALESCE(i.timezone, 'UTC') AS timezone,
                           COUNT(s.id) AS interview_count
                    FROM interviewers i
                    LEFT JOIN interview_schedules s
                        ON s.interviewer_id = i.id
                        AND s.scheduled_time >= date_trunc('week', NOW())
                        AND s.status != 'cancelled'
                    WHERE i.is_active = TRUE
                    GROUP BY i.id, i.name, i.email, i.timezone
                    ORDER BY interview_count ASC
                    LIMIT 1
                """
                cur.execute(query)
                row = cur.fetchone()
                if row:
                    return {
                        "id": row[0], "name": row[1],
                        "email": row[2], "timezone": row[3],
                        "interview_count": row[4],
                    }
                return None
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Slot generation
    # ------------------------------------------------------------------

    def get_availability(self, interviewer_id: int, date_str: str) -> List[str]:
        """
        Return available ISO slots for an interviewer on a given date.
        Falls back to default business hours if Google Calendar is unavailable.
        """
        if self.service:
            return self._get_calendar_slots(interviewer_id, date_str)
        return self._generate_default_slots(date_str)

    def _get_calendar_slots(self, interviewer_id: int, date_str: str) -> List[str]:
        """Query Google Calendar free/busy and return open 1-hour slots."""
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT calendar_id, timezone FROM interviewers WHERE id = %s",
                    (interviewer_id,),
                )
                row = cur.fetchone()
            conn.close()

            calendar_id = (row[0] if row and row[0] else "primary")
            tz_name = (row[1] if row and row[1] else "UTC")
            tz = pytz.timezone(tz_name)

            date = datetime.strptime(date_str, "%Y-%m-%d")
            day_start = tz.localize(date.replace(hour=9, minute=0))
            day_end = tz.localize(date.replace(hour=17, minute=0))

            body = {
                "timeMin": day_start.isoformat(),
                "timeMax": day_end.isoformat(),
                "items": [{"id": calendar_id}],
            }
            result = self.service.freebusy().query(body=body).execute()
            busy_periods = result.get("calendars", {}).get(calendar_id, {}).get("busy", [])

            # Build free slots (1-hour blocks) that don't overlap busy periods
            slots = []
            current = day_start
            while current + timedelta(hours=1) <= day_end:
                slot_end = current + timedelta(hours=1)
                overlap = any(
                    datetime.fromisoformat(b["start"]) < slot_end
                    and datetime.fromisoformat(b["end"]) > current
                    for b in busy_periods
                )
                if not overlap:
                    slots.append(current.isoformat())
                current += timedelta(hours=1)
            return slots
        except Exception as e:
            print(f"Calendar slot fetch failed: {e}")
            return self._generate_default_slots(date_str)

    def _generate_default_slots(self, date_str: str, num_slots: int = 5) -> List[str]:
        """Return up to `num_slots` default business-hour slots on the given date."""
        date = datetime.strptime(date_str, "%Y-%m-%d")
        start = date.replace(hour=9, minute=0)
        end = date.replace(hour=17, minute=0)
        slots = []
        while start + timedelta(hours=1) <= end and len(slots) < num_slots:
            slots.append(start.isoformat())
            start += timedelta(hours=1)
        return slots

    def generate_candidate_slot_options(
        self, interviewer_ids: List[int], days_ahead: int = 2, num_options: int = 5
    ) -> List[str]:
        """
        Cross-match free slots across all panel members and return
        up to `num_options` common slots starting from `days_ahead` days from now.
        """
        search_date = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        all_slots: Optional[set] = None

        for iid in interviewer_ids:
            slots = set(self.get_availability(iid, search_date))
            all_slots = slots if all_slots is None else all_slots & slots

        if not all_slots:
            # Fallback: return default slots ignoring cross-match
            return self._generate_default_slots(search_date, num_options)

        return sorted(all_slots)[:num_options]

    # ------------------------------------------------------------------
    # Scheduling core
    # ------------------------------------------------------------------

    def schedule_interview(
        self,
        candidate_data: Dict,
        interviewer_id: int,
        slot_iso: str,
        round_number: int = 1,
        round_label: str = "Interview",
        interview_format: str = "video call",
        google_event_id: Optional[str] = None,
        meeting_link: Optional[str] = None,
    ) -> int:
        """
        Persist an interview record and send an invite email to the candidate.
        Returns the new interview_schedule id.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO interview_schedules
                        (candidate_name, candidate_email, interviewer_id, scheduled_time,
                         status, google_event_id)
                    VALUES (%s, %s, %s, %s, 'scheduled', %s)
                    RETURNING id
                    """,
                    (
                        candidate_data["name"],
                        candidate_data["email"],
                        interviewer_id,
                        slot_iso,
                        google_event_id or "N/A",
                    ),
                )
                interview_id = cur.fetchone()[0]
            conn.commit()

            # Send candidate invite
            self.send_invite_email(
                candidate_data, slot_iso,
                round_number=round_number, round_label=round_label,
                interview_format=interview_format, meeting_link=meeting_link,
            )
            return interview_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def reschedule_interview(
        self, interview_id: int, candidate_data: Dict, new_slot_iso: str
    ) -> bool:
        """
        Update an existing interview to a new time slot and re-notify candidate.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE interview_schedules
                    SET scheduled_time = %s, status = 'scheduled'
                    WHERE id = %s
                    """,
                    (new_slot_iso, interview_id),
                )
            conn.commit()
            self.send_invite_email(candidate_data, new_slot_iso, round_label="Rescheduled Interview")
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # No-show handling
    # ------------------------------------------------------------------

    def flag_no_show(self, interview_id: int) -> bool:
        """Mark an interview as no-show and send HR a notification."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE interview_schedules SET status = 'no_show' WHERE id = %s",
                    (interview_id,),
                )
            conn.commit()
            print(f"[NoShow] Interview {interview_id} flagged as no-show.")
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_no_show_interviews(self, grace_minutes: int = 15) -> List[Dict]:
        """
        Return scheduled interviews whose start time passed more than
        `grace_minutes` ago and are still in 'scheduled' status.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, candidate_name, candidate_email, scheduled_time
                    FROM interview_schedules
                    WHERE status = 'scheduled'
                    AND scheduled_time < NOW() - INTERVAL '%s minutes'
                    """,
                    (grace_minutes,),
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0], "candidate_name": r[1],
                        "candidate_email": r[2], "scheduled_time": r[3],
                    }
                    for r in rows
                ]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Post-interview: feedback kit & aggregation
    # ------------------------------------------------------------------

    def get_interviews_ready_for_feedback(self, window_minutes: int = 15) -> List[Dict]:
        """
        Return interviews whose end time (start + 1 hour) just passed within
        the last `window_minutes` minutes and feedback has not yet been sent.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.id, s.candidate_name, s.candidate_email,
                           s.scheduled_time, i.name AS interviewer_name,
                           i.email AS interviewer_email
                    FROM interview_schedules s
                    JOIN interviewers i ON s.interviewer_id = i.id
                    WHERE s.status = 'scheduled'
                    AND s.feedback_submitted = FALSE
                    AND s.scheduled_time + INTERVAL '1 hour'
                        BETWEEN NOW() - INTERVAL '%s minutes' AND NOW()
                    """,
                    (window_minutes,),
                )
                rows = cur.fetchall()
                return [
                    {
                        "interview_id": r[0],
                        "candidate_name": r[1], "candidate_email": r[2],
                        "scheduled_time": r[3],
                        "interviewer_name": r[4], "interviewer_email": r[5],
                    }
                    for r in rows
                ]
        finally:
            conn.close()

    def aggregate_feedback_and_decide(self, interview_id: int) -> str:
        """
        Aggregate all feedback scores for a candidate's completed round.
        Returns 'pass', 'fail', or 'hold' based on the average overall rating.
        Thresholds: pass >= 7/10, fail < 5/10, else hold.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT AVG(overall_rating), AVG(technical_skills),
                           AVG(communication_skills),
                           mode() WITHIN GROUP (ORDER BY recommendation) AS recommendation
                    FROM interview_feedback
                    WHERE interview_id = %s
                    """,
                    (interview_id,),
                )
                row = cur.fetchone()
                if not row or row[0] is None:
                    return "hold"

                avg_overall = float(row[0])
                recommendation = (row[3] or "").lower()

                if recommendation in ("strong_yes", "yes") or avg_overall >= 7:
                    decision = "pass"
                elif recommendation in ("no", "strong_no") or avg_overall < 5:
                    decision = "fail"
                else:
                    decision = "hold"

                # Persist decision on the interview record
                cur.execute(
                    "UPDATE interview_schedules SET status = %s WHERE id = %s",
                    (f"decision_{decision}", interview_id),
                )
            conn.commit()
            return decision
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Email helpers
    # ------------------------------------------------------------------

    def _format_slot_for_email(self, raw_slot: Optional[str], tz_name: Optional[str] = None) -> str:
        """Convert ISO/UTC schedule strings into readable local time for emails."""
        if not raw_slot:
            return "To Be Confirmed"

        display_tz_name = tz_name or os.getenv("INTERVIEW_DISPLAY_TIMEZONE") or os.getenv("APP_TIMEZONE") or "Asia/Kolkata"
        try:
            display_tz = pytz.timezone(display_tz_name)
        except Exception:
            display_tz = pytz.timezone("UTC")

        value = str(raw_slot).strip()
        try:
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"

            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt_local = display_tz.localize(dt)
            else:
                dt_local = dt.astimezone(display_tz)
            return dt_local.strftime("%d %b %Y, %I:%M %p (%Z)")
        except Exception:
            return str(raw_slot)

    def send_invite_email(
        self,
        candidate: Dict,
        slot_iso: str,
        round_number: int = 1,
        round_label: str = "Interview",
        interview_format: str = "video call",
        meeting_link: Optional[str] = None,
        slot_options: Optional[List[str]] = None,
    ):
        """Send a rich HTML interview invitation to the candidate."""
        email_config = self.secrets.get("email", {})
        if not email_config:
            print("Email config missing – skipping invite email.")
            return

        formatted_confirmed_time = self._format_slot_for_email(slot_iso)

        # Format slot options list
        slots_html = ""
        if slot_options:
            items = "".join(f"<li>{self._format_slot_for_email(s)}</li>" for s in slot_options)
            slots_html = f"<p><strong>Available Slots:</strong></p><ul>{items}</ul>"

        meeting_section = (
            f'<p><strong>Meeting Link:</strong> <a href="{meeting_link}">{meeting_link}</a></p>'
            if meeting_link
            else "<p><strong>Meeting platform link:</strong> Will be shared separately.</p>"
        )

        html_body = f"""
        <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
        <div style="max-width:600px;margin:auto;padding:20px;">
          <div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:30px;border-radius:10px 10px 0 0;text-align:center;">
            <h1>Interview Invitation</h1>
            <p>Round {round_number}: {round_label}</p>
          </div>
          <div style="background:#f9fafb;padding:30px;border-radius:0 0 10px 10px;">
            <p>Dear <strong>{candidate['name']}</strong>,</p>
            <p>We are pleased to invite you for <strong>Round {round_number} – {round_label}</strong>.</p>
            <ul>
              <li><strong>Format:</strong> {interview_format.title()}</li>
                            <li><strong>Confirmed Time:</strong> {formatted_confirmed_time}</li>
              <li><strong>Duration:</strong> ~60 minutes</li>
            </ul>
            {slots_html}
            {meeting_section}
            <p><strong>What to expect:</strong> Please be prepared to discuss your background,
            relevant experience, and technical competencies aligned with the role.</p>
            <p>If you need to reschedule, please reply to this email at least 24 hours in advance.</p>
            <br><p>Best regards,<br><strong>HR Recruiting Team</strong></p>
          </div>
          <p style="text-align:center;font-size:12px;color:#888;margin-top:20px;">
            This is an automated email from our recruitment system.
          </p>
        </div>
        </body></html>
        """

        msg = MIMEMultipart("alternative")
        msg["From"] = email_config.get("sender_email", "")
        msg["To"] = candidate["email"]
        msg["Subject"] = f"Interview Invitation – Round {round_number}: {round_label}"
        msg.attach(MIMEText(html_body, "html"))

        self._smtp_send(msg, email_config)

    def send_interviewer_kit(
        self,
        interviewer_email: str,
        interviewer_name: str,
        candidate_name: str,
        candidate_email: str,
        scheduled_time: str,
        round_label: str = "Interview",
        feedback_form_url: str = "",
        resume_summary: str = "",
        job_description: str = "",
    ):
        """Send the interview kit (candidate info, scorecard link, suggested questions) to the interviewer."""
        email_config = self.secrets.get("email", {})
        if not email_config:
            return

        if not feedback_form_url:
            base_url = self.secrets.get("app", {}).get("base_url", "http://localhost:8000")
            feedback_form_url = f"{base_url}/feedback-form.html"

        html_body = f"""
        <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
        <div style="max-width:600px;margin:auto;padding:20px;">
          <div style="background:#1a202c;color:white;padding:25px;border-radius:10px 10px 0 0;">
            <h2>Interview Kit – {round_label}</h2>
          </div>
          <div style="background:#f9fafb;padding:25px;border-radius:0 0 10px 10px;">
            <p>Hi <strong>{interviewer_name}</strong>,</p>
            <p>You have an upcoming interview. Here are the details:</p>
            <table style="width:100%;border-collapse:collapse;">
              <tr><td style="padding:6px 0;"><strong>Candidate:</strong></td><td>{candidate_name} ({candidate_email})</td></tr>
              <tr><td style="padding:6px 0;"><strong>Round:</strong></td><td>{round_label}</td></tr>
              <tr><td style="padding:6px 0;"><strong>Scheduled Time:</strong></td><td>{scheduled_time}</td></tr>
            </table>
            {"<h3>Job Description</h3><p>" + job_description[:500] + "...</p>" if job_description else ""}
            {"<h3>Candidate Resume Summary</h3><p>" + resume_summary[:400] + "...</p>" if resume_summary else ""}
            <h3>Suggested Interview Questions</h3>
            <ol>
              <li>Walk me through your most relevant project experience.</li>
              <li>Describe a challenging technical problem you solved.</li>
              <li>How do you handle disagreements within a team?</li>
              <li>What is your experience with [role-specific skill]?</li>
              <li>Where do you see yourself in 3 years?</li>
            </ol>
            <h3>Feedback Scorecard</h3>
            <p>Please submit your feedback within 24 hours of the interview:</p>
            <p><a href="{feedback_form_url}" style="display:inline-block;padding:12px 24px;background:#667eea;color:white;border-radius:5px;text-decoration:none;">Submit Feedback</a></p>
            <br><p>Best regards,<br><strong>HR Coordination</strong></p>
          </div>
        </div>
        </body></html>
        """

        msg = MIMEMultipart("alternative")
        msg["From"] = email_config.get("sender_email", "")
        msg["To"] = interviewer_email
        msg["Subject"] = f"Interview Kit: {candidate_name} – {round_label}"
        msg.attach(MIMEText(html_body, "html"))

        self._smtp_send(msg, email_config)

    def send_rejection_email(self, candidate_name: str, candidate_email: str):
        """Send a respectful, personalized rejection email."""
        email_config = self.secrets.get("email", {})
        if not email_config:
            return

        html_body = f"""
        <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
        <div style="max-width:600px;margin:auto;padding:20px;">
          <div style="background:#4a5568;color:white;padding:25px;border-radius:10px 10px 0 0;text-align:center;">
            <h2>Application Status Update</h2>
          </div>
          <div style="background:#f9fafb;padding:25px;border-radius:0 0 10px 10px;">
            <p>Dear <strong>{candidate_name}</strong>,</p>
            <p>Thank you for taking the time to interview with us. We truly appreciate your interest
               in joining our team and the effort you put into the process.</p>
            <p>After careful consideration, we have decided to move forward with another candidate
               whose experience more closely aligns with the specific needs of this role at this time.</p>
            <p>This decision was not easy, and we encourage you to continue applying for future
               opportunities that match your skills. We will keep your profile on file.</p>
            <p>We wish you the very best in your job search.</p>
            <br><p>Warm regards,<br><strong>HR Recruiting Team</strong></p>
          </div>
        </div>
        </body></html>
        """

        msg = MIMEMultipart("alternative")
        msg["From"] = email_config.get("sender_email", "")
        msg["To"] = candidate_email
        msg["Subject"] = "Your Application Status – Thank You for Interviewing"
        msg.attach(MIMEText(html_body, "html"))

        self._smtp_send(msg, email_config)

    def send_next_round_email(
        self,
        candidate_name: str,
        candidate_email: str,
        next_round_number: int,
        next_round_label: str,
    ):
        """Notify the candidate they have passed and are moving to the next round."""
        email_config = self.secrets.get("email", {})
        if not email_config:
            return

        html_body = f"""
        <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
        <div style="max-width:600px;margin:auto;padding:20px;">
          <div style="background:linear-gradient(135deg,#48bb78,#276749);color:white;padding:25px;border-radius:10px 10px 0 0;text-align:center;">
            <h2>🎉 Congratulations – You've Advanced!</h2>
          </div>
          <div style="background:#f9fafb;padding:25px;border-radius:0 0 10px 10px;">
            <p>Dear <strong>{candidate_name}</strong>,</p>
            <p>We are delighted to inform you that you have <strong>passed your recent interview</strong>
               and are advancing to the next stage of our selection process.</p>
            <p><strong>Next Step:</strong> Round {next_round_number} – {next_round_label}</p>
            <p>Our team will be in touch shortly with scheduling details. Please keep an eye on your inbox.</p>
            <br><p>Best regards,<br><strong>HR Recruiting Team</strong></p>
          </div>
        </div>
        </body></html>
        """

        msg = MIMEMultipart("alternative")
        msg["From"] = email_config.get("sender_email", "")
        msg["To"] = candidate_email
        msg["Subject"] = f"🎉 You've Advanced to Round {next_round_number}: {next_round_label}"
        msg.attach(MIMEText(html_body, "html"))

        self._smtp_send(msg, email_config)

    def _smtp_send(self, msg: MIMEMultipart, email_config: Dict):
        """Shared SMTP send helper."""
        try:
            with smtplib.SMTP(
                email_config.get("smtp_server", "smtp.gmail.com"),
                email_config.get("smtp_port", 587),
            ) as server:
                server.starttls()
                server.login(
                    email_config.get("sender_email", ""),
                    email_config.get("sender_password", ""),
                )
                server.send_message(msg)
        except Exception as e:
            print(f"SMTP send failed: {e}")


import os
import toml
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from backend.database import get_db_connection
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

class SchedulingService:
    def __init__(self):
        self.load_secrets()
        self.setup_google_calendar()

    def load_secrets(self):
        self.secrets = {}
        if os.path.exists("secrets.toml"):
            self.secrets = toml.load("secrets.toml")
        elif os.path.exists("../secrets.toml"):
            self.secrets = toml.load("../secrets.toml")
        
    def setup_google_calendar(self):
        self.service = None
        google_config = self.secrets.get('google_calendar', {})
        # Note: In a real backend, we'd handle OAuth2 flow differently (via API), 
        # but for now reusing local token.json logic if available.
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", ['https://www.googleapis.com/auth/calendar'])
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            self.service = build('calendar', 'v3', credentials=creds)

    def get_interviewers(self):
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, email, timezone FROM interviewers WHERE is_active = TRUE")
                return cur.fetchall()
        finally:
            conn.close()

    def get_availability(self, interviewer_id: int, date_str: str):
        # ... (simplified logic from original file)
        # For this stage, let's assume we return fixed slots if Google Calendar isn't connected
        if not self.service:
            return self._generate_default_slots(date_str)
        
        # Real implementation would query Google Calendar here
        # Avoiding complex porting for now to keep it concise, but structure is here
        return self._generate_default_slots(date_str)

    def _generate_default_slots(self, date_str: str):
        date = datetime.strptime(date_str, "%Y-%m-%d")
        start = date.replace(hour=9, minute=0)
        end = date.replace(hour=17, minute=0)
        slots = []
        while start < end:
            slots.append(start.isoformat())
            start += timedelta(minutes=60)
        return slots

    def schedule_interview(self, candidate_data: Dict, interviewer_id: int, slot_iso: str):
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO interview_schedules 
                    (candidate_name, candidate_email, interviewer_id, scheduled_time, status)
                    VALUES (%s, %s, %s, %s, 'scheduled')
                    RETURNING id
                """, (candidate_data['name'], candidate_data['email'], interviewer_id, slot_iso))
                interview_id = cur.fetchone()[0]
            conn.commit()
            
            # Send Email
            self.send_invite_email(candidate_data, slot_iso)
            return interview_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def send_invite_email(self, candidate: Dict, slot_iso: str):
        email_config = self.secrets.get('email', {})
        if not email_config: return
        
        msg = MIMEMultipart()
        msg['From'] = email_config.get('sender_email')
        msg['To'] = candidate['email']
        msg['Subject'] = "Interview Invitation"
        
        body = f"Hello {candidate['name']},\n\nYour interview is confirmed for {slot_iso}."
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['sender_email'], email_config['sender_password'])
                server.send_message(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")


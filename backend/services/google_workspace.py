"""Workspace OAuth clients for one recruitment team's calendar and sender."""

import base64
import os
from datetime import timedelta
from email.message import EmailMessage
from hashlib import sha256

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def client(service, version):
    creds = Credentials.from_authorized_user_file(os.environ["GOOGLE_TOKEN_FILE"])
    return build(service, version, credentials=creds, cache_discovery=False)


def calendar_id():
    return os.environ.get("GOOGLE_CALENDAR_ID", "primary")


def availability(start, end):
    key = calendar_id()
    result = (
        client("calendar", "v3")
        .freebusy()
        .query(
            body={
                "timeMin": start.isoformat(),
                "timeMax": end.isoformat(),
                "items": [{"id": key}],
            }
        )
        .execute()["calendars"][key]
    )
    if result.get("errors"):
        raise RuntimeError("Google could not verify availability")
    return result["busy"]


def event_key(key, run_id):
    return sha256(f"{key}:recruitment:{run_id}".encode()).hexdigest()


def schedule(run_id, address, start, reschedule):
    from datetime import datetime

    beginning = datetime.fromisoformat(start)
    end = beginning + timedelta(hours=1)
    events = client("calendar", "v3").events()
    key = calendar_id()
    event_id = event_key(key, run_id)
    body = {
        "summary": "Recruitment interview",
        "attendees": [{"email": address}],
        "start": {"dateTime": start},
        "end": {"dateTime": end.isoformat()},
    }
    if reschedule:
        return events.patch(
            calendarId=key, eventId=event_id, body=body, sendUpdates="all"
        ).execute()["id"]
    try:
        return events.insert(
            calendarId=key, body=dict(body, id=event_id), sendUpdates="all"
        ).execute()["id"]
    except HttpError as exc:
        if exc.resp.status != 409:
            raise
        existing = events.get(calendarId=key, eventId=event_id).execute()
        if (
            existing.get("status") == "cancelled"
            or datetime.fromisoformat(existing["start"]["dateTime"]) != beginning
            or address
            not in [person.get("email") for person in existing.get("attendees", [])]
        ):
            raise RuntimeError("Conflicting calendar event") from exc
        return existing["id"]


def send_mail(address, subject, text):
    message = EmailMessage()
    message["To"] = address
    message["Subject"] = subject
    message.set_content(text)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return (
        client("gmail", "v1")
        .users()
        .messages()
        .send(userId="me", body={"raw": raw})
        .execute()["id"]
    )


def reschedule_conflict(run_id, start, end):
    """Allow a move that overlaps the application's own previous event."""
    key = calendar_id()
    own_id = event_key(key, run_id)
    events = client("calendar", "v3").events()
    page = None
    while True:
        result = events.list(
            calendarId=key,
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            pageToken=page,
        ).execute()
        if any(
            item["id"] != own_id
            and item.get("status") != "cancelled"
            and item.get("transparency") != "transparent"
            for item in result["items"]
        ):
            return True
        page = result.get("nextPageToken")
        if not page:
            return False

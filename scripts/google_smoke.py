"""Send one authorized test email and exercise one fresh calendar event."""

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.services import google_workspace as google


def main():
    address = os.environ["GOOGLE_TEST_RECIPIENT"]
    key = os.environ["GOOGLE_CALENDAR_ID"]
    if not address or not key:
        raise RuntimeError("Set a designated test recipient and calendar")
    start = (datetime.now(timezone.utc) + timedelta(days=7)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    later = start + timedelta(hours=2)
    if google.availability(start, start + timedelta(hours=1)) or google.availability(
        later, later + timedelta(hours=1)
    ):
        raise RuntimeError("Both test slots must be free")
    run = uuid4().hex
    event = google.schedule(run, address, start.isoformat(), False)
    try:
        assert google.schedule(run, address, later.isoformat(), True) == event
        events = google.client("calendar", "v3").events()
        confirmed = events.get(calendarId=key, eventId=event).execute()
        assert datetime.fromisoformat(confirmed["start"]["dateTime"]) == later
        message = google.send_mail(
            address,
            "Recruitment integration check",
            "Synthetic test of the authorized recruitment sender.",
        )
        print(
            "Calendar booking and reschedule verified. Gmail accepted message", message
        )
    finally:
        google.client("calendar", "v3").events().delete(
            calendarId=key, eventId=event, sendUpdates="all"
        ).execute()


if __name__ == "__main__":
    main()

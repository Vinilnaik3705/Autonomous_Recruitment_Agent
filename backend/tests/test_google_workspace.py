from base64 import urlsafe_b64decode
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from unittest.mock import MagicMock

import pytest

from backend.services import google_workspace as google


def test_gmail_mime_and_provider_receipt(monkeypatch):
    messages = MagicMock()
    service = MagicMock()
    service.users.return_value.messages.return_value = messages
    monkeypatch.setattr(google, "client", lambda *_: service)
    messages.send.return_value.execute.return_value = {"id": "receipt"}
    assert google.send_mail("fixture@example.org", "Interview", "Tomorrow") == "receipt"
    args = messages.send.call_args.kwargs
    assert args["userId"] == "me"
    mime = message_from_bytes(urlsafe_b64decode(args["body"]["raw"]))
    assert mime["To"] == "fixture@example.org" and mime["Subject"] == "Interview"
    assert mime.get_payload().strip() == "Tomorrow"


def test_calendar_fails_closed_and_reschedule_ignores_own_event(monkeypatch):
    service = MagicMock()
    monkeypatch.setattr(google, "client", lambda *_: service)
    monkeypatch.setenv("GOOGLE_CALENDAR_ID", "team")
    service.freebusy.return_value.query.return_value.execute.return_value = {
        "calendars": {"team": {"errors": [{"reason": "forbidden"}]}}
    }
    start = datetime.now(timezone.utc)
    with pytest.raises(RuntimeError):
        google.availability(start, start + timedelta(hours=1))
    result = service.events.return_value.list.return_value.execute
    result.return_value = {"items": [{"id": google.event_key("team", 4)}]}
    assert not google.reschedule_conflict(4, start, start + timedelta(hours=1))
    result.return_value["items"].append({"id": "external"})
    assert google.reschedule_conflict(4, start, start + timedelta(hours=1))

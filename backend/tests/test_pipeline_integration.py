"""Run against a migrated disposable PostgreSQL database with PIPELINE_INTEGRATION=1."""

import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4

import pytest
from docx import Document
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    os.getenv("PIPELINE_INTEGRATION") != "1", reason="requires disposable PostgreSQL"
)


def test_screen_to_onboarding(monkeypatch):
    from backend import pipeline_api as api
    from backend.workers import pipeline
    from backend.schemas.resume import ResumeFields
    from backend.orchestration.screening import build_screening_graph

    client = TestClient(api.app)
    sent, bookings = [], []
    monkeypatch.setattr(api, "availability", lambda *_: [])
    monkeypatch.setattr(api, "reschedule_conflict", lambda *_: False)
    monkeypatch.setattr(
        pipeline.google_workspace,
        "schedule",
        lambda *args: bookings.append(args) or "event",
    )
    monkeypatch.setattr(
        pipeline.google_workspace,
        "send_mail",
        lambda *args: sent.append(args) or "message",
    )
    monkeypatch.setattr(pipeline.LocalMiniLM, "encode", lambda self, text: [0.1] * 384)
    monkeypatch.setattr(
        pipeline,
        "build_screening_graph",
        lambda embedder: build_screening_graph(
            embedder=embedder, extractor=lambda text: ResumeFields(skills=["Python"])
        ),
    )

    def account():
        name = uuid4().hex
        email = f"{name}@example.org"
        credentials = {"email": email, "password": "synthetic-test-password"}
        response = client.post("/auth/register", json=dict(credentials, username=name))
        assert response.status_code == 200, response.text
        auth = client.post("/auth/login", json=credentials).json()
        return (
            auth["user"]["id"],
            email,
            {"Authorization": "Bearer " + auth["access_token"]},
        )

    hr, _, staff = account()
    _, email, candidate = account()
    assert client.get("/runs", headers=candidate).status_code == 403
    with pipeline.transaction() as cur:
        cur.execute("UPDATE users SET role='recruiter' WHERE id=%s", (hr,))
    doc = Document()
    doc.add_paragraph("Python developer")
    buf = BytesIO()
    doc.save(buf)
    key = str(uuid4())

    def submit():
        response = client.post(
            "/runs",
            headers=dict(staff, **{"Idempotency-Key": key}),
            files={"file": ("test.docx", buf.getvalue())},
            data={
                "email": email,
                "job_description": "Python engineer",
                "required_skills": "Python",
            },
        )
        assert response.status_code == 202, response.text
        return response.json()["id"]

    run = submit()
    assert submit() == run

    def deliver(kind):
        with pipeline.transaction() as cur:
            cur.execute(
                "SELECT id FROM recruitment_actions WHERE run_id=%s AND kind=%s",
                (run, kind),
            )
            action = cur.fetchone()["id"]
        pipeline.deliver(action)
        pipeline.deliver(action)

    deliver("invitation")
    assert len(sent) == 1
    code = sent[0][2].split()[-1]
    assert (
        client.post(
            "/applications/claim", data={"code": code}, headers=candidate
        ).status_code
        == 200
    )
    pipeline.screen(run)
    pipeline.screen(run)
    row = client.get("/runs", headers=staff).json()[0]
    assert row["id"] == run and row["result"]["score"]["combined_score"] == 1

    def move(target, expected=200, **fields):
        response = client.post(
            f"/runs/{run}/stage", headers=staff, json=dict(target=target, **fields)
        )
        assert response.status_code == expected, response.text

    move("shortlisted")
    start = datetime.now(timezone.utc) + timedelta(days=2)
    move("interview_scheduled", start=start.isoformat())
    deliver("book")
    move("interview_scheduled", start=(start + timedelta(days=1)).isoformat())
    deliver("reschedule")
    assert len(bookings) == 2
    move("interviewed")
    move("feedback_received", note="Reviewed work sample")
    move("selected")
    move("offer_sent", 403, note="Synthetic test offer")
    with pipeline.transaction() as cur:
        cur.execute("UPDATE users SET role='hr' WHERE id=%s", (hr,))
    move("offer_sent", note="Synthetic test offer")
    deliver("offer")
    move("onboarding", checklist=["Complete induction"])
    deliver("onboarding")
    move("complete", note="Induction completed")
    view = client.get("/applications", headers=candidate).json()
    assert view[0]["stage"] == "complete" and "result" not in view[0]
    assert len(sent) == 3


def test_reconcile_unknown_delivery(monkeypatch):
    from backend import pipeline_api as api
    from backend.workers import pipeline

    client = TestClient(api.app)
    monkeypatch.setattr(
        pipeline.google_workspace,
        "send_mail",
        lambda *args: (_ for _ in ()).throw(TimeoutError()),
    )
    with pipeline.transaction() as cur:
        cur.execute(
            """INSERT INTO agent_runs(owner_id,request_key,email,filename,job_description,required_skills,stage)
                     VALUES(1,%s,'offer@example.org','sample.pdf','demo','{}','selected') RETURNING id""",
            (str(uuid4()),),
        )
        run = cur.fetchone()["id"]
        cur.execute(
            """INSERT INTO recruitment_actions(run_id,kind,body) VALUES(%s,'offer',
                    '{"subject":"Offer","text":"Synthetic"}') RETURNING id""",
            (run,),
        )
        action = cur.fetchone()["id"]
    with pytest.raises(TimeoutError):
        pipeline.deliver(action)
    pipeline.deliver(action)
    api.app.dependency_overrides[api.get_current_user] = lambda: {
        "user_id": 7,
        "role": "hr",
    }
    try:
        response = client.post(
            f"/actions/{action}/reconcile",
            json={
                "delivered": True,
                "provider_id": "test-message",
                "evidence": "Reviewed synthetic sent record",
            },
        )
        assert response.status_code == 200, response.text
        with pipeline.transaction() as cur:
            cur.execute("SELECT stage FROM agent_runs WHERE id=%s", (run,))
            assert cur.fetchone()["stage"] == "offer_sent"
    finally:
        api.app.dependency_overrides.pop(api.get_current_user)

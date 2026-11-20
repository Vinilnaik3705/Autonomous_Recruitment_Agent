import os
from uuid import uuid4

import numpy as np
import psycopg
import pytest
from pgvector.psycopg import register_vector
from psycopg import sql

from backend.db.migrate import migrate
from backend.config import get_settings

pytestmark = pytest.mark.skipif(
    os.getenv("PIPELINE_INTEGRATION") != "1", reason="requires test PostgreSQL"
)


@pytest.fixture
def database(monkeypatch):
    source = get_settings().database_url
    name = "recruitment_test_" + uuid4().hex
    url = psycopg.conninfo.make_conninfo(source, dbname=name)
    with psycopg.connect(source, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            monkeypatch.setenv("DATABASE_URL", url)
            get_settings.cache_clear()
            assert len(migrate(url)) == 9
            assert migrate(url) == []
            yield url
        finally:
            get_settings.cache_clear()
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


def test_constraints_and_pgvector(database):
    with psycopg.connect(database, autocommit=True) as conn:
        register_vector(conn)
        owner = conn.execute(
            "INSERT INTO users(email,full_name,password_hash) VALUES (%s,%s,%s) RETURNING id",
            ("staff@example.org", "Test HR", "fixture"),
        ).fetchone()[0]
        job = conn.execute(
            "INSERT INTO jobs(title,description,created_by) VALUES (%s,%s,%s) RETURNING id",
            ("Engineer", "Python", owner),
        ).fetchone()[0]
        insert = "INSERT INTO applications(job_id,email,full_name,status,embedding) VALUES (%s,%s,%s,%s,%s)"
        vector = np.ones(384, dtype=np.float32)
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(insert, (job, "alice@example.org", "Alice", "invalid", vector))
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute(
                insert, (job + 1, "alice@example.org", "Alice", "applied", vector)
            )
        conn.execute(insert, (job, "alice@example.org", "Alice", "applied", vector))
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(insert, (job, "alice@example.org", "Alice", "applied", vector))
        distance = conn.execute(
            "SELECT embedding <=> %s FROM applications ORDER BY embedding <=> %s LIMIT 1",
            (vector, vector),
        ).fetchone()[0]
        assert distance == pytest.approx(0)


def test_login_create_job_upload_and_score(database, monkeypatch):
    from io import BytesIO
    from docx import Document
    from fastapi.testclient import TestClient
    from backend.pipeline_api import app
    from backend.auth import hash_password
    from backend.embeddings.provider import LocalMiniLM
    from backend.orchestration.screening import build_screening_graph
    from backend.schemas.resume import ResumeFields
    from backend.workers import pipeline

    monkeypatch.setattr(LocalMiniLM, "encode", lambda self, text: [0.1] * 384)
    monkeypatch.setattr(
        pipeline,
        "build_screening_graph",
        lambda: build_screening_graph(
            extractor=lambda text: ResumeFields(
                name="Synthetic Candidate", skills=["Python"]
            )
        ),
    )
    with psycopg.connect(database) as conn:
        conn.execute(
            "INSERT INTO users(email,full_name,password_hash,role) VALUES (%s,%s,%s,'hr')",
            ("staff@example.org", "Test HR", hash_password("example-password")),
        )

    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"email": "staff@example.org", "password": "example-password"},
        )
        assert response.status_code == 200, response.text
        staff = {"Authorization": "Bearer " + response.json()["access_token"]}
        response = client.post(
            "/jobs",
            headers=staff,
            json={
                "title": "Engineer",
                "description": "Python engineering",
                "required_skills": ["Python"],
            },
        )
        assert response.status_code == 201, response.text
        job_id = response.json()["id"]

        response = client.post(
            "/auth/register",
            json={
                "email": "candidate@example.org",
                "full_name": "Synthetic Candidate",
                "password": "candidate-password",
            },
        )
        assert response.status_code == 201, response.text
        candidate = {"Authorization": "Bearer " + response.json()["access_token"]}
        document = Document()
        document.add_paragraph("Synthetic Candidate. Python.")
        buffer = BytesIO()
        document.save(buffer)
        response = client.post(
            "/applications",
            headers=candidate,
            data={"job_id": job_id, "full_name": "Synthetic Candidate"},
            files={"file": ("resume.docx", buffer.getvalue())},
        )
        assert response.status_code == 202, response.text
        application_id = response.json()["id"]

        with psycopg.connect(database) as conn:
            run_id = conn.execute(
                "SELECT id FROM agent_runs WHERE application_id=%s AND action='screen'",
                (application_id,),
            ).fetchone()[0]
        pipeline.screen(run_id)
        pipeline.screen(run_id)
        response = client.get("/applications", headers=candidate)
        assert response.status_code == 200, response.text
        assert response.json()[0]["status"] == "screened"
        assert response.json()[0]["match_score"] == pytest.approx(1)
        assert (
            client.get(f"/jobs/{job_id}/matches", headers=candidate).status_code == 403
        )
        response = client.get(f"/jobs/{job_id}/matches", headers=staff)
        assert response.status_code == 200, response.text
        assert response.json()[0]["similarity"] == pytest.approx(1)

        from datetime import datetime, timedelta, timezone

        def move(target, **body):
            response = client.post(
                f"/applications/{application_id}/stage",
                headers=staff,
                json={"target": target, **body},
            )
            assert response.status_code == 200, response.text

        with psycopg.connect(database) as conn:
            interviewer_id = conn.execute(
                """INSERT INTO users(email,full_name,password_hash,role)
                   VALUES (%s,%s,%s,'interviewer') RETURNING id""",
                ("panel@example.org", "Test Panel", hash_password("example-password")),
            ).fetchone()[0]
        monkeypatch.setattr("backend.pipeline_api.availability", lambda start, end: [])
        monkeypatch.setattr(
            pipeline.google_workspace, "schedule", lambda *args: "test-calendar-event"
        )
        sent = []
        monkeypatch.setattr(
            pipeline.google_workspace,
            "send_mail",
            lambda *args: sent.append(args) or "test-mail",
        )
        move("shortlisted")
        move(
            "interview_scheduled",
            interviewer_id=interviewer_id,
            scheduled_start=(
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat(),
        )

        def deliver(action):
            with psycopg.connect(database) as conn:
                delivery_id = conn.execute(
                    "SELECT id FROM agent_runs WHERE application_id=%s AND action=%s",
                    (application_id, action),
                ).fetchone()[0]
            pipeline.deliver(delivery_id)
            pipeline.deliver(delivery_id)

        deliver("book")
        move("interviewed")
        login = client.post(
            "/auth/login",
            json={"email": "panel@example.org", "password": "example-password"},
        )
        assert login.status_code == 200
        panel = {"Authorization": "Bearer " + login.json()["access_token"]}
        assert (
            client.get("/interviews/assigned", headers=panel).json()[0][
                "application_id"
            ]
            == application_id
        )
        response = client.post(
            f"/interviews/{application_id}/feedback",
            headers=panel,
            json={
                "comments": "Clear answers",
                "scores": {"technical": 4},
                "recommendation": "select",
            },
        )
        assert response.status_code == 200, response.text
        move("selected")
        move("offer_sent", offer_text="Synthetic offer")
        deliver("offer")
        assert len(sent) == 1
        move("onboarding", checklist=["Confirm start date"])
        path = f"/applications/{application_id}/onboarding"
        task_id = client.get(path, headers=candidate).json()[0]["id"]
        assert (
            client.post(f"{path}/{task_id}", headers=candidate).json()["status"]
            == "submitted"
        )
        assert (
            client.post(f"{path}/{task_id}", headers=staff).json()["status"]
            == "verified"
        )
        move("complete")
        assert (
            client.get("/applications", headers=candidate).json()[0]["status"]
            == "complete"
        )

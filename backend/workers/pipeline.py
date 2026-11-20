"""Postgres owns pending work. Beat republishes IDs after broker outages."""

from contextlib import closing, contextmanager
from datetime import datetime, timedelta

from celery import Celery
from psycopg2.extras import Json, RealDictCursor

from backend.config import get_settings
from backend.database import get_db_connection
from backend.embeddings.provider import LocalMiniLM
from backend.orchestration.screening import build_screening_graph
from backend.services import google_workspace
from backend.services.screening_score import score_candidate

app = Celery("pipeline", broker=get_settings().redis_url)
app.conf.update(
    task_ignore_result=True,
    task_default_queue="light",
    task_routes={"recruitment.screen": {"queue": "heavy"}},
    beat_schedule={"dispatch": {"task": "recruitment.dispatch", "schedule": 15.0}},
)


@contextmanager
def transaction():
    with closing(get_db_connection()) as conn, conn, conn.cursor(
        cursor_factory=RealDictCursor
    ) as cur:
        yield cur


@app.task(name="recruitment.dispatch")
def dispatch():
    with transaction() as cur:
        cur.execute(
            "SELECT id FROM agent_runs WHERE screening_state='queued' ORDER BY id LIMIT 100"
        )
        for row in cur.fetchall():
            screen.delay(row["id"])
        cur.execute(
            "UPDATE recruitment_actions SET state='uncertain' WHERE state='sending' AND claimed_at < now()-interval '15 minutes'"
        )
        cur.execute(
            "SELECT id FROM recruitment_actions WHERE state='pending' AND available_at<=now() ORDER BY id LIMIT 100"
        )
        for row in cur.fetchall():
            deliver.delay(row["id"])


@app.task(name="recruitment.screen")
def screen(run_id):
    with transaction() as cur:
        cur.execute(
            "SELECT * FROM agent_runs WHERE id=%s AND screening_state='queued' FOR UPDATE SKIP LOCKED",
            (run_id,),
        )
        run = cur.fetchone()
        if not run:
            return
        encoder = LocalMiniLM()
        try:
            data = build_screening_graph(embedder=encoder).invoke(
                {"file_bytes": bytes(run["document"]), "filename": run["filename"]}
            )
            fields = data["fields"]
            vector = data["embedding"]
            score = score_candidate(
                vector,
                encoder.encode(run["job_description"]),
                fields["skills"],
                run["required_skills"],
            )
        except Exception:
            cur.execute(
                "UPDATE agent_runs SET screening_state='failed' WHERE id=%s", (run_id,)
            )
            raise_after_commit = True
        else:
            cur.execute(
                """UPDATE agent_runs SET screening_state='done', stage='screened', document=NULL,
                           embedding=%s::vector, result=%s WHERE id=%s""",
                (
                    str(vector),
                    Json({"fields": fields, "score": score.model_dump()}),
                    run_id,
                ),
            )
            raise_after_commit = False
    if raise_after_commit:
        raise RuntimeError(
            "Screening failed; review model configuration or document and retry"
        )


@app.task(name="recruitment.deliver")
def deliver(action_id):
    with transaction() as cur:
        cur.execute(
            """UPDATE recruitment_actions SET state='sending', claimed_at=now()
                       WHERE id=%s AND state='pending' AND available_at<=now() RETURNING *""",
            (action_id,),
        )
        action = cur.fetchone()
        if not action:
            return
        cur.execute(
            "SELECT email, stage, interview_at FROM agent_runs WHERE id=%s",
            (action["run_id"],),
        )
        run = cur.fetchone()
    body = action["body"]
    kind = action["kind"]
    try:
        if kind in ("book", "reschedule"):
            provider_id = google_workspace.schedule(
                action["run_id"], run["email"], body["start"], kind == "reschedule"
            )
        elif kind == "reminder" and (
            run["stage"] != "interview_scheduled"
            or run["interview_at"] != datetime.fromisoformat(body["start"])
        ):
            provider_id = None
        else:
            provider_id = google_workspace.send_mail(
                run["email"], body["subject"], body["text"]
            )
    except Exception:
        with transaction() as cur:
            cur.execute(
                "UPDATE recruitment_actions SET state='uncertain' WHERE id=%s",
                (action_id,),
            )
        raise
    with transaction() as cur:
        record_delivery(cur, action, provider_id)


def record_delivery(cur, action, provider_id):
    """Apply delivery and its resulting stage in the same transaction."""
    action_id, kind, body = action["id"], action["kind"], action["body"]
    cur.execute(
        "UPDATE recruitment_actions SET state=%s, provider_id=%s WHERE id=%s",
        ("sent" if provider_id else "cancelled", provider_id, action_id),
    )
    if kind in ("book", "reschedule"):
        start = datetime.fromisoformat(body["start"])
        cur.execute(
            "UPDATE agent_runs SET stage='interview_scheduled', interview_at=%s WHERE id=%s",
            (start, action["run_id"]),
        )
        reminder = {
            "subject": "Interview reminder",
            "text": f"Your interview begins at {start.isoformat()}.",
            "start": body["start"],
        }
        cur.execute(
            """INSERT INTO recruitment_actions(run_id,kind,body,available_at)
                      SELECT %s,'reminder',%s,%s WHERE %s > now() ON CONFLICT DO NOTHING""",
            (
                action["run_id"],
                Json(reminder),
                start - timedelta(hours=1),
                start - timedelta(hours=1),
            ),
        )
    elif kind == "offer":
        cur.execute(
            "UPDATE agent_runs SET stage='offer_sent' WHERE id=%s", (action["run_id"],)
        )

"""Dispatch database-backed recruitment work through Celery and Redis."""

from datetime import datetime, timedelta, timezone
import logging

from celery import Celery

from backend.config import get_settings
from backend.database import worker_conn
from backend.db.queries import applications, interviews, resumes, runs
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


@app.task(name="recruitment.dispatch")
def dispatch():
    with worker_conn() as conn:
        runs.expire_dispatches(conn)
        pending = runs.due(conn)
    for row in pending:
        (screen if row["action"] == "screen" else deliver).delay(row["id"])


@app.task(name="recruitment.screen")
def screen(run_id):
    with worker_conn() as conn:
        run = runs.lock(conn, run_id)
        if (
            not run
            or run["action"] != "screen"
            or run["details"]["delivery"] != "queued"
        ):
            return
        application_id = run["application_id"]
        source = applications.screening_input(conn, application_id)
        if not source:
            return
        try:
            path = source["resume_path"]
            data = build_screening_graph().invoke(
                {"file_bytes": resumes.read(conn, path), "filename": path}
            )
            score = score_candidate(
                data["embedding"],
                source["job_embedding"].to_list(),
                data["fields"]["skills"],
                source["required_skills"],
            )
        except Exception:
            runs.update(conn, run_id, "failed", "failed")
            logging.getLogger(__name__).exception("Screening failed for run %s", run_id)
        else:
            applications.save_screening(conn, application_id, data, score)
            runs.record_transition(conn, application_id, "applied", "screened")
            runs.update(conn, run_id, "success", "done")


@app.task(name="recruitment.deliver")
def deliver(run_id):
    with worker_conn() as conn:
        run = runs.lock(conn, run_id)
        if (
            not run
            or run["action"] == "screen"
            or run["details"]["delivery"] != "queued"
        ):
            return
        application = applications.lock(conn, run["application_id"])
        body = run["details"]
        expected = body.get("expected_status")
        if not application or (expected and application["status"] != expected):
            runs.update(conn, run_id, "success", "cancelled")
            return
        if run["action"] == "reminder":
            appointment = interviews.get(conn, run["application_id"])
            if not appointment or appointment[
                "scheduled_start"
            ] != datetime.fromisoformat(body["start"]):
                runs.update(conn, run_id, "success", "cancelled")
                return
        runs.update(
            conn,
            run_id,
            "running",
            "sending",
            claimed_at=datetime.now(timezone.utc).isoformat(),
        )

    try:
        if run["action"] in {"book", "reschedule"}:
            receipt = google_workspace.schedule(
                run["application_id"],
                application["email"],
                body["start"],
                run["action"] == "reschedule",
            )
        else:
            receipt = google_workspace.send_mail(
                application["email"], body["subject"], body["text"]
            )
        if not receipt:
            raise RuntimeError("Provider returned no receipt")
    except Exception:
        with worker_conn() as conn:
            runs.update(conn, run_id, "failed", "uncertain")
        raise
    with worker_conn() as conn:
        record_delivery(conn, run, receipt)


def record_delivery(conn, run, receipt):
    application_id = run["application_id"]
    action, body = run["action"], run["details"]
    if action in {"book", "reschedule"}:
        start = datetime.fromisoformat(body["start"])
        interview = interviews.save(
            conn,
            application_id,
            body["interviewer_id"],
            start,
            start + timedelta(hours=1),
            receipt,
        )
        applications.set_status(conn, application_id, "interview_scheduled")
        runs.record_transition(
            conn, application_id, body["expected_status"], "interview_scheduled"
        )
        due = start - timedelta(hours=1)
        if due > datetime.now(timezone.utc):
            runs.enqueue(
                conn,
                application_id,
                "reminder",
                f"remind:{interview['id']}:{run['id']}",
                {
                    "start": body["start"],
                    "subject": "Interview reminder",
                    "text": f"Your interview starts at {body['start']}.",
                    "expected_status": "interview_scheduled",
                },
                due,
            )
    elif action == "offer":
        applications.offer_sent(conn, application_id)
        runs.record_transition(conn, application_id, "selected", "offer_sent")
    elif action == "reminder":
        interviews.mark_reminded(conn, application_id)
    runs.update(conn, run["id"], "success", "sent", provider_id=receipt, text=None)

"""Use the configured test Redis broker and real Celery consumers."""
import os
from time import monotonic, sleep
from uuid import uuid4

import pytest


@pytest.mark.skipif(os.getenv("PIPELINE_BROKER_TEST") != "1", reason="requires disposable Redis and Postgres")
def test_dispatch_through_light_and_heavy_queues(monkeypatch):
    from celery.contrib.testing.worker import start_worker
    from backend.workers import pipeline

    observed = []
    # Provider test double raises on a deliberately invalid document. The heavy
    # worker must persist a failure rather than leave the run stuck in queued.
    with pipeline.transaction() as cur:
        cur.execute("""INSERT INTO agent_runs(owner_id,request_key,email,filename,document,job_description,required_skills)
                       VALUES(1,%s,'queue@example.org','invalid.pdf',%s,'Testing','{}') RETURNING id""",
                    (str(uuid4()), b"invalid pdf"))
        run = cur.fetchone()["id"]
        cur.execute("""INSERT INTO recruitment_actions(run_id,kind,body) VALUES(%s,'invitation',
                       '{"subject":"Queue test","text":"Synthetic"}')""", (run,))
    monkeypatch.setattr(pipeline.google_workspace, "send_mail", lambda *args: observed.append(args) or "test-message")
    with start_worker(pipeline.app, perform_ping_check=False, queues=["light","heavy"], pool="solo"):
        pipeline.dispatch.delay()
        deadline = monotonic() + 30
        while monotonic() < deadline:
            with pipeline.transaction() as cur:
                cur.execute("""SELECT screening_state,state FROM agent_runs r JOIN recruitment_actions a
                               ON r.id=a.run_id WHERE r.id=%s""", (run,))
                row = cur.fetchone()
            if row["screening_state"] == "failed" and row["state"] == "sent":
                break
            sleep(.2)
        else:
            pytest.fail(f"Worker did not finish: {row}")
    assert len(observed) == 1

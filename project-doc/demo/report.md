# A human-approved recruitment workflow with durable task execution

**Abstract** — The migration implements a single-team recruitment workflow from resume submission through onboarding. It uses PostgreSQL to record stage transitions and outbound work, Celery to process queued actions, and LangGraph to coordinate resume parsing, field extraction and embedding. A test deployment verified a full synthetic hiring path against PostgreSQL. A second run used a local language model and MiniLM. External delivery acceptance requires a designated Google test account.

## I. System requirements

Staff need to see the state of an application after a worker restart, retry a failed screening job and avoid duplicate offers. Candidates need a view of their own application without access to internal evaluations. The system preserves HR control over rejections and offers. Calendar reservations and Gmail deliveries can fail independently of a database transaction.

## II. Implementation

The Vite client authenticates through FastAPI. The API looks up the active account and role in PostgreSQL for protected requests. Candidate registration grants a student role, and claiming an application requires an invitation emailed to the registered address. Uploads use a unique key per submitting account. The API writes the run and invitation action in one transaction.

Celery Beat discovers due work every fifteen seconds. A heavy worker locks the queued run and executes three LangGraph nodes. The first reads PDF or DOCX text. The second validates factual fields against a Pydantic schema. The third uses all-MiniLM-L6-v2 to produce a 384-dimensional vector. The worker scores the resume against the job description and commits its results together. With required skills present, the configured score combines 70% clipped cosine similarity and 30% required-skill coverage. A job without listed skills uses only the semantic score. Reviewers determine the next stage.

## III. External delivery and approvals

Calendar booking checks availability, reserves a pending slot and uses an event ID derived from the application and calendar. Rescheduling updates that event. The light worker schedules a reminder and suppresses obsolete reminders after a move. Gmail does not participate in the PostgreSQL transaction. If the remote response is ambiguous, HR records verification before another send. HR enters written offer terms and approves the offer. After acceptance, the team records checklist items and completion evidence.

## IV. Verification

| Experiment | Observation |
| --- | --- |
| Original backend suite | Seven failures reproduced before fixes, including JWT validation and a formatted phone number. |
| Database rehearsal | A PostgreSQL 16 synthetic legacy backup was restored and upgraded with pgvector and Alembic. Its test resume remained present. |
| Queue exercise | Redis-backed Celery consumers handled heavy and light messages and persisted the screening failure for an invalid PDF. |
| Model exercise | Ollama with Qwen2.5 0.5B extracted the synthetic name, email, both listed skills and education. MiniLM returned 384 values. |
| Workflow integration | Tests exercised screening, feedback, permission checks, repeated delivery, scheduling, rescheduling, onboarding and candidate access with controlled Google responses. |

## V. Limits and acceptance

These checks establish software behavior on synthetic fixtures. They do not establish hiring accuracy, fairness, or precision and recall on a labeled applicant population. The deployment serves one HR team. Historical n8n applications remain in their original tables. A user-authorized Google mailbox and test calendar are required to confirm invitations and delivery in the actual account. Rollback requires the previous deployment and its backup.

## Implementation references

1. Screening graph and score calculation, `backend/orchestration/screening.py` and `backend/services/screening_score.py`.
2. Stage and delivery transactions, `backend/pipeline_api.py` and `backend/workers/pipeline.py`.
3. Reproducible acceptance checks, `backend/tests/test_pipeline_integration.py`, `backend/tests/test_queue_integration.py`, and `scripts/google_smoke.py`.

# Migration status

The migration runs from `backend.pipeline_api:app`, the Vite dashboard in `frontend/src/workspace`, and `backend.workers.pipeline:app`. The main README contains the current deployment and verification procedures. Pages describing n8n and the old dashboard refer to the previous deployment.

| Check | Evidence |
| --- | --- |
| Schema migration | A fresh PostgreSQL 16 database enabled pgvector. A synthetic legacy database was dumped, restored and upgraded with its resume row intact. |
| Screening and hiring stages | The integration suite executes a LangGraph with test providers and persists real vectors and stages. It checks HR offer approval, rescheduling, an invitation claim and onboarding. |
| Delivery failure | An ambiguous Gmail response records an uncertain delivery. Repeated tasks leave it pending human review. HR can record a provider ID or confirm non-delivery before a retry. |
| Worker integration | A Redis broker and Celery consumer processed both heavy and light queues. |
| Real model exercise | A synthetic DOCX passed through Ollama (Qwen2.5 0.5B), LangGraph and MiniLM. The graph returned the expected name, email, two skills, education and a 384-value vector. |
| External acceptance | A live authorized mailbox, calendar and designated recipient must be exercised before production signoff. |

## Demo script

1. Register a candidate account and provision a separate verified staff account with the HR role. Use only a test mailbox and calendar.
2. Submit a synthetic DOCX and a short job description. Show the invitation and link the candidate account. Show parsed fields and score components on the staff dashboard.
3. Shortlist and schedule a future interview. Verify the event in Calendar and its attendee. Reschedule to a free slot and verify the event ID is unchanged.
4. Mark the interview complete, record feedback and select the candidate. Verify a recruiter cannot issue the offer. Issue it as HR and confirm the test mailbox received it once.
5. After acceptance, enter the onboarding checklist. Verify the candidate can see it and HR can record completion.
6. Exercise ambiguous delivery only in the integration suite. Use a provider message or event ID to reconcile a real ambiguous outcome.

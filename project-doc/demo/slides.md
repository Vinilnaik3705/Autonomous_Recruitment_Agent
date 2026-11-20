---
title: Autonomous Recruitment Agent
subtitle: Workflow migration and acceptance demo
---

# One application from intake to onboarding

- HR submits a synthetic resume and job description.
- Candidates claim an invitation to see their own application.
- The demo ends with an approved offer and a verified onboarding checklist.

# Screening with LangGraph

1. Parse selectable PDF text or DOCX paragraphs.
2. Extract schema-validated fields with Gemini or Ollama.
3. Compute a 384-dimensional MiniLM embedding and persist the score.
4. Show staff the matching and missing skills for human review.

# Work survives process restarts

- PostgreSQL records each run and its pending actions.
- Beat sends due work to heavy and light Celery queues through Redis.
- A database lock prevents duplicate screening writes.
- The staff dashboard exposes failed screening for retry.

# Calendar and Gmail

- Availability is checked before creating or moving an interview.
- The application retains the same Google event ID when a meeting moves.
- A delivery with an unknown outcome requires reconciliation.
- The live acceptance script uses a designated test mailbox and calendar.

# Human decisions

- Recruiters record interview feedback.
- Only HR can issue an offer or reject a candidate.
- Candidates see the checklist after acceptance.
- Staff record evidence before marking onboarding complete.

# Demonstrated and pending

- PostgreSQL backup restoration preserved a synthetic legacy resume.
- A Redis worker consumed both queues.
- Ollama extracted the synthetic resume fields and MiniLM returned 384 values.
- Live Google account verification remains the merge gate.

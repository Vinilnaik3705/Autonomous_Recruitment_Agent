# Backend API Guide

Base URL (local): `http://127.0.0.1:8000`

Interactive API docs:

- `/docs`
- `/redoc`

## Authentication

Prefix: `/auth`

Key endpoints:

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/social` (Google)
- `GET /auth/me`
- `GET /auth/permissions`

Roles supported:

- `super_admin`
- `recruiter`
- `interviewer`
- `candidate`

## Resume and matching

- `POST /resume/analyze`
- `POST /resume/upload-batch`
- `POST /resume/sentiment`
- `POST /resume/sentiment-text`
- `POST /resume/score-with-embeddings`
- `POST /resume/match`
- `POST /utils/extract-text`
- `POST /utils/generate-jd`

## Jobs and screening

- `POST /jobs/create`
- `POST /jobs/batch-screen`
- `POST /jobs/n8n-proxy`
- `GET /jobs/interviewstatus`
- `DELETE /jobs/clear-interviews`

## Candidate portal

Prefix: `/candidate`

- `GET /candidate/my-status`

## OA (Online Assessment)

Prefix: `/oa`

- `GET /oa/launch`
- `GET /oa/complete`
- `POST /oa/submit-result`
- `POST /oa/submit-result-webhook`
- `POST /oa/submit-from-url`
- `GET /oa/candidate/{candidate_email}/status`

Key behavior:

- Score normalized to out-of-10 scale
- Database updated immediately
- Thank-you email queued in background
- Scheduling workflow triggered for passing score

## Interview lifecycle

- `POST /interview/schedule`
- `GET /interview/availability/{interviewer_id}`
- `POST /interview/slot-options`
- `POST /interview/assign-panel`
- `POST /interview/reschedule`
- `POST /interview/no-show`
- `POST /interview/check-no-shows`
- `POST /interview/send-feedback-kits`
- `POST /interview/decision/{interview_id}`
- `POST /interview/feedback`
- `POST /interview/feedback/collect`

## Notifications

Prefix: `/notifications`

- `POST /notifications`
- `GET /notifications`
- `PATCH /notifications/{notification_id}/read`

## Email templates/utilities

Prefix: `/email`

Examples:

- `POST /email/resume-shortlisted`
- `POST /email/oa-practice`
- `POST /email/oa-original`
- `POST /email/oa-completion-thank-you`
- `POST /email/interview-invite`
- `POST /email/interview-reminder`

## Onboarding

- `POST /onboarding/initiate`

## Notes for API consumers

- Use Bearer token for protected endpoints.
- For file uploads, use multipart/form-data.
- OA callback payloads are tolerant to multiple key names.
- For production, lock CORS, rotate secrets, and enforce stricter auth policies.

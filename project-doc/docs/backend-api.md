# Backend API

Base URL (local): http://localhost:8000

## Resume and matching

- POST /resume/upload-batch
- POST /resume/analyze
- POST /resume/sentiment (accepts either file upload or raw text via `req_text` parameter)
- POST /resume/score-with-embeddings
- POST /resume/match
- POST /utils/extract-text
- POST /utils/generate-jd

## Interview scheduling and operations

- POST /interview/schedule
- GET /interview/availability/{interviewer_id}
- POST /interview/slot-options
- POST /interview/assign-panel
- POST /interview/reschedule
- POST /interview/no-show
- POST /interview/check-no-shows
- POST /interview/send-feedback-kits
- POST /interview/decision/{interview_id}

## Feedback and status

- POST /interview/feedback
- POST /interview/feedback/collect
- GET /jobs/interviewstatus
- DELETE /jobs/clear-interviews
- GET /feedback-form.html

## Onboarding

- POST /onboarding/initiate

## Additional routers

The application also mounts router-based endpoints from:

- auth_router
- job_router
- candidate_router
- notification_router
- oa_router
- email_router

Use FastAPI interactive docs for full request and response schemas:
http://localhost:8000/docs

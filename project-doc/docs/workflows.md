# Workflow Guide

This page explains the major business workflows implemented in the project.

## 1) Resume screening workflow

1. Recruiter creates a job description.
2. Recruiter uploads one or many resumes.
3. Backend extracts text and candidate metadata.
4. Embeddings-based scoring compares resume against JD.
5. Candidates are saved/updated across tracking tables.
6. Shortlisted candidates proceed to OA invitation step.

## 2) OA invitation and completion workflow

1. Candidate receives official OA link via email template.
2. Link can be launched through backend tracking endpoint.
3. After completion, OA score is submitted via:
   - direct endpoint, or
   - webhook endpoint, or
   - callback URL with query tokens/report URL.
4. Score is normalized and saved immediately in DB.
5. Completion thank-you email is generated/sent in background.
6. Passing candidates trigger scheduling workflow webhook.

## 3) Interview scheduling workflow

1. System identifies available interview slots.
2. Interview is scheduled and stored.
3. Candidate receives invite details.
4. Reminder logic supports scheduled reminder windows.
5. No-show checker can auto-flag missed interviews.
6. Reschedule endpoint supports slot updates.

## 4) Feedback and decision workflow

1. Interviewers submit feedback scorecards.
2. Aggregation endpoint computes decision signal.
3. Outcome routing:
   - pass: next-round communication
   - fail: rejection communication
   - hold: manual HR review path

## 5) Onboarding initiation workflow

1. Final candidate data is posted to onboarding endpoint.
2. Onboarding service creates onboarding task entry.
3. Follow-up actions can be expanded in future iterations.

## n8n integration touchpoints

Current integration points include:

- Screening trigger webhook
- Interview scheduling trigger webhook
- Reminder/no-show periodic automation
- OA submission callback handling

To run with n8n successfully:

- Ensure n8n is reachable on configured URL.
- Import required workflow JSON files.
- Validate webhook URLs used by frontend/backend.

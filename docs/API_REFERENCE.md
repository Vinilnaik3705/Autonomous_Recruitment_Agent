# API Reference

Complete API documentation for the Autonomous Recruitment Agent backend.

**Base URL:** `http://localhost:8000`  
**API Docs (Interactive):** `http://localhost:8000/docs`

---

## 📋 Table of Contents

- [Authentication](#authentication)
- [Resume Management](#resume-management)
- [Job Management](#job-management)
- [Interview Scheduling](#interview-scheduling)
- [Feedback System](#feedback-system)
- [Admin Operations](#admin-operations)
- [Error Handling](#error-handling)

---

## 🔐 Authentication

### Firebase Authentication

All API requests (except public endpoints) require a valid Firebase ID token in the Authorization header.

**Header Format:**
```http
Authorization: Bearer <firebase_id_token>
```

**Getting a Token (Client-side):**
```javascript
import { getAuth } from 'firebase/auth';

const auth = getAuth();
const token = await auth.currentUser.getIdToken();
```

---

## 📄 Resume Management

### Upload Single Resume

**Endpoint:** `POST /resume/analyze`

**Description:** Upload and analyze a single resume file.

**Request:**
```http
POST /resume/analyze
Content-Type: multipart/form-data

file: <resume_file.pdf>
user_id: 1
```

**Supported Formats:** `.pdf`, `.docx`, `.doc`

**Response:**
```json
{
  "status": "success",
  "file_id": 123,
  "data": {
    "filename": "john_doe_resume.pdf",
    "name": "John Doe",
    "email": "john.doe@example.com",
    "mobile": "+1-555-0100",
    "skills": "Python, Java, React, Docker, AWS",
    "education": "B.Tech in Computer Science, IIT Delhi, CGPA: 8.5",
    "raw_text": "..."
  }
}
```

**Error Responses:**
```json
// Invalid file format
{
  "detail": "Unsupported file type: .txt"
}

// Missing file
{
  "detail": "No file provided"
}
```

---

### Upload Multiple Resumes (Batch)

**Endpoint:** `POST /resume/upload-batch`

**Description:** Upload multiple resumes for background processing.

**Request:**
```http
POST /resume/upload-batch
Content-Type: multipart/form-data

files: <resume1.pdf>
files: <resume2.pdf>
files: <resume3.pdf>
user_id: 1
```

**Response:**
```json
{
  "status": "processing",
  "message": "Received 3 files for processing in background."
}
```

---

### Resume Sentiment Analysis

**Endpoint:** `POST /resume/sentiment`

**Description:** Analyze sentiment and generate summary of a resume.

**Request (File Upload):**
```http
POST /resume/sentiment
Content-Type: multipart/form-data

file: <resume.pdf>
```

**Request (Text Input):**
```http
POST /resume/sentiment?req_text=<resume_text>
```

**Response:**
```json
{
  "filename": "john_doe_resume.pdf",
  "status": "success",
  "analysis": {
    "sentiment": "positive",
    "confidence": 0.85,
    "summary": "Experienced software engineer with strong technical background...",
    "key_strengths": [
      "5+ years of experience",
      "Strong full-stack skills",
      "Cloud expertise"
    ]
  }
}
```

---

### Score Resume Against Job Description

**Endpoint:** `POST /resume/score-with-embeddings`

**Description:** Calculate AI match score for a resume against a job description.

**Request:**
```json
{
  "resume_text": "John Doe\nSoftware Engineer\n5 years experience in Python, React...",
  "job_description": "We are looking for a Full Stack Developer with Python and React experience..."
}
```

**Response:**
```json
{
  "candidate_name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+1-555-0100",
  "skills": "Python, React, Docker, AWS",
  "score": 85.5,
  "summary": "Match score: 85.50/100 (Threshold: 35)",
  "shortlisted": true
}
```

---

### Match Resumes to Job

**Endpoint:** `POST /resume/match`

**Description:** Find top matching candidates for a job description.

**Request:**
```json
{
  "jd_text": "We need a Senior Python Developer with Django experience...",
  "top_k": 5,
  "job_id": "JOB-2024-001"
}
```

**Response:**
```json
{
  "matches": [
    {
      "candidate_name": "Alice Johnson",
      "email": "alice@example.com",
      "phone": "+1-555-0101",
      "skills": ["Python", "Django", "PostgreSQL"],
      "score": 92.3,
      "shortlisted": true
    },
    {
      "candidate_name": "Bob Smith",
      "email": "bob@example.com",
      "phone": "+1-555-0102",
      "skills": ["Python", "Flask", "Docker"],
      "score": 87.1,
      "shortlisted": true
    }
  ]
}
```

---

### Extract Text from File

**Endpoint:** `POST /utils/extract-text`

**Description:** Extract raw text from a document file.

**Request:**
```http
POST /utils/extract-text
Content-Type: multipart/form-data

file: <document.pdf>
```

**Response:**
```json
{
  "filename": "document.pdf",
  "text": "Extracted text content here..."
}
```

---

## 💼 Job Management

### Create Job Posting

**Endpoint:** `POST /jobs/create`

**Description:** Create a new job posting.

**Request:**
```json
{
  "title": "Senior Full Stack Developer",
  "description": "We are seeking an experienced developer...",
  "requirements": "5+ years experience, Python, React, Docker",
  "department": "Engineering",
  "location": "Remote",
  "salary_range": "$100k - $150k"
}
```

**Response:**
```json
{
  "job_id": "JOB-2024-001",
  "status": "created",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### Generate Job Description

**Endpoint:** `POST /utils/generate-jd`

**Description:** Use AI to generate a job description.

**Request:**
```json
{
  "role": "Full Stack Developer",
  "experience": "3-5 years",
  "skills": "Python, React, PostgreSQL, Docker"
}
```

**Response:**
```json
{
  "jd_text": "Job Title: Full Stack Developer\n\nWe are seeking a talented Full Stack Developer with 3-5 years of experience...\n\nKey Responsibilities:\n- Design and develop scalable web applications\n- Work with Python and React frameworks\n...\n\nRequired Skills:\n- Python (Django/FastAPI)\n- React.js\n- PostgreSQL\n- Docker"
}
```

---

### Get All Jobs

**Endpoint:** `GET /jobs/list`

**Description:** Retrieve all job postings.

**Query Parameters:**
- `status`: Filter by status (active, closed, draft)
- `limit`: Number of results (default: 50)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "JOB-2024-001",
      "title": "Senior Full Stack Developer",
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z",
      "applicants_count": 45
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

---

## 📅 Interview Scheduling

### Schedule Interview

**Endpoint:** `POST /interview/schedule`

**Description:** Schedule an interview for a candidate.

**Request:**
```json
{
  "candidate_email": "john.doe@example.com",
  "candidate_name": "John Doe",
  "interviewer_id": 5,
  "slot_iso": "2024-01-20T14:00:00Z"
}
```

**Response:**
```json
{
  "status": "scheduled",
  "interview_id": 42,
  "scheduled_time": "2024-01-20T14:00:00Z",
  "interviewer": "Jane Smith",
  "calendar_invite_sent": true
}
```

**Error Response (Already Scheduled):**
```json
{
  "status": "already_scheduled",
  "interview_id": 38,
  "message": "Candidate already has an active interview schedule"
}
```

---

### Get Availability

**Endpoint:** `GET /interview/availability/{interviewer_id}`

**Description:** Check interviewer availability for a specific date.

**Query Parameters:**
- `date`: Date in YYYY-MM-DD format

**Example:**
```http
GET /interview/availability/5?date=2024-01-20
```

**Response:**
```json
{
  "interviewer_id": 5,
  "interviewer_name": "Jane Smith",
  "date": "2024-01-20",
  "available_slots": [
    "2024-01-20T10:00:00Z",
    "2024-01-20T14:00:00Z",
    "2024-01-20T16:00:00Z"
  ],
  "booked_slots": [
    "2024-01-20T11:00:00Z"
  ]
}
```

---

### Get Slot Options for Panel

**Endpoint:** `POST /interview/slot-options`

**Description:** Find common available slots for multiple interviewers.

**Request:**
```json
{
  "interviewer_ids": [5, 7, 9],
  "days_ahead": 1,
  "search_window_days": 7,
  "num_options": 5
}
```

**Response:**
```json
{
  "slots": [
    {
      "time": "2024-01-21T14:00:00Z",
      "available_interviewers": [5, 7, 9]
    },
    {
      "time": "2024-01-22T10:00:00Z",
      "available_interviewers": [5, 7]
    }
  ]
}
```

---

### Assign Interview Panel

**Endpoint:** `POST /interview/assign-panel`

**Description:** Get panel template and assign interviewers for a specific round.

**Request:**
```json
{
  "job_title": "Software Engineer",
  "round_number": 1
}
```

**Response:**
```json
{
  "round_info": {
    "round": 1,
    "round_label": "Technical Round",
    "department": "Engineering",
    "panel_size": 2
  },
  "assigned_interviewer": {
    "id": 5,
    "name": "Jane Smith",
    "email": "jane@company.com",
    "specialization": ["Python", "System Design"]
  },
  "full_template": [...]
}
```

---

### Reschedule Interview

**Endpoint:** `POST /interview/reschedule`

**Description:** Move an interview to a new time slot.

**Request:**
```json
{
  "interview_id": 42,
  "candidate_email": "john.doe@example.com",
  "candidate_name": "John Doe",
  "new_slot_iso": "2024-01-22T15:00:00Z"
}
```

**Response:**
```json
{
  "status": "rescheduled",
  "interview_id": 42,
  "new_time": "2024-01-22T15:00:00Z",
  "notification_sent": true
}
```

---

### Flag No-Show

**Endpoint:** `POST /interview/no-show`

**Description:** Mark a candidate as a no-show for an interview.

**Request:**
```json
{
  "interview_id": 42
}
```

**Response:**
```json
{
  "status": "no_show_flagged",
  "interview_id": 42,
  "candidate_notified": true
}
```

---

### Check for No-Shows (Automated)

**Endpoint:** `POST /interview/check-no-shows`

**Description:** Scan for interviews that should have started and flag no-shows.

**Query Parameters:**
- `grace_minutes`: Grace period after scheduled time (default: 15)

**Response:**
```json
{
  "flagged_count": 3,
  "interview_ids": [45, 47, 51]
}
```

---

## 📝 Feedback System

### Submit Feedback

**Endpoint:** `POST /interview/feedback`

**Description:** Submit interview feedback (interviewer use).

**Request:**
```json
{
  "interview_id": 42,
  "technical_skills": 8,
  "communication_skills": 9,
  "overall_rating": 8,
  "recommendation": "strong_yes",
  "detailed_feedback": "Excellent problem-solving skills. Strong communication..."
}
```

**Recommendation Values:**
- `strong_yes`: Highly recommend
- `yes`: Recommend
- `hold`: Need more evaluation
- `no`: Do not recommend
- `strong_no`: Strongly against

**Response:**
```json
{
  "status": "submitted",
  "interview_id": 42,
  "feedback_id": 128
}
```

---

### Collect Feedback (Form Submission)

**Endpoint:** `POST /interview/feedback/collect`

**Description:** Collect feedback from external form submissions.

**Request:**
```json
{
  "interview_id": 42,
  "candidate_email": "john.doe@example.com",
  "candidate_name": "John Doe",
  "round_label": "Technical Round 1",
  "technical_score": 8,
  "communication_score": 9,
  "cultural_fit_score": 8,
  "overall_rating": 8,
  "recommendation": "accept",
  "comments": "Strong technical skills and great cultural fit."
}
```

**Response:**
```json
{
  "status": "submitted",
  "interview_id": 42,
  "workflow_triggered": true,
  "workflow_status_code": 200
}
```

---

### Send Feedback Kits

**Endpoint:** `POST /interview/send-feedback-kits`

**Description:** Send feedback forms to interviewers after completed interviews.

**Query Parameters:**
- `window_minutes`: Time window after interview end (default: 15)

**Response:**
```json
{
  "kits_sent": 5,
  "interview_ids": [42, 43, 45, 47, 48]
}
```

---

### Make Interview Decision

**Endpoint:** `POST /interview/decision/{interview_id}`

**Description:** Aggregate feedback and make final decision.

**Response:**
```json
{
  "decision": "pass",
  "interview_id": 42,
  "candidate": "John Doe",
  "next_action": "Schedule next round",
  "aggregated_scores": {
    "technical": 8.5,
    "communication": 9.0,
    "overall": 8.7
  }
}
```

**Decision Values:**
- `pass`: Move to next round
- `fail`: Reject candidate
- `hold`: Keep for further review

---

## 🔧 Admin Operations

### Get Interview Status

**Endpoint:** `GET /jobs/interviewstatus`

**Description:** Get comprehensive interview status for all candidates.

**Query Parameters:**
- `force_fresh`: Force fresh data (bypass cache)

**Response:**
```json
{
  "total_candidates": 150,
  "by_status": {
    "shortlisted": 45,
    "interviewed": 30,
    "selected": 10,
    "rejected": 65
  },
  "candidates": [
    {
      "name": "John Doe",
      "email": "john.doe@example.com",
      "status": "interviewed",
      "ai_score": 85.5,
      "interview_date": "2024-01-20T14:00:00Z",
      "feedback_received": true
    }
  ]
}
```

---

### Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

---

### Database Health

**Endpoint:** `GET /health/db`

**Response:**
```json
{
  "database": "connected",
  "latency_ms": 12
}
```

---

### Metrics

**Endpoint:** `GET /api/metrics`

**Description:** Prometheus metrics endpoint.

**Response:** (Prometheus format)
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",endpoint="/resume/analyze"} 1523

# HELP resume_processing_time Resume processing duration
# TYPE resume_processing_time histogram
resume_processing_time_bucket{le="1.0"} 845
```

---

## ⚠️ Error Handling

### Standard Error Response Format

```json
{
  "detail": "Error message describing what went wrong",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Request completed successfully |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input parameters |
| 401 | Unauthorized | Missing or invalid auth token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Temporary unavailability |

---

## 🔒 Rate Limiting

**Default Limits:**
- 100 requests per minute per IP
- 1000 requests per hour per user

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1610712000
```

---

## 📊 Pagination

For endpoints returning lists, use pagination parameters:

**Query Parameters:**
- `limit`: Number of items per page (max: 100)
- `offset`: Number of items to skip

**Example:**
```http
GET /jobs/list?limit=20&offset=40
```

**Response includes pagination metadata:**
```json
{
  "data": [...],
  "pagination": {
    "total": 250,
    "limit": 20,
    "offset": 40,
    "has_more": true
  }
}
```

---

## 🧪 Testing APIs

### Using cURL

```bash
# Upload resume
curl -X POST http://localhost:8000/resume/analyze \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@resume.pdf" \
  -F "user_id=1"

# Score resume
curl -X POST http://localhost:8000/resume/score-with-embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "John Doe...",
    "job_description": "We need..."
  }'
```

### Using Python

```python
import requests

# Upload resume
url = "http://localhost:8000/resume/analyze"
files = {"file": open("resume.pdf", "rb")}
data = {"user_id": 1}
response = requests.post(url, files=files, data=data)
print(response.json())
```

---

**API Version:** 1.0  
**Last Updated:** 2024-01-15  
**For Interactive Docs:** Visit `http://localhost:8000/docs`

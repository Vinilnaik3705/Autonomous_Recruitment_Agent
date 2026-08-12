# Architecture Documentation

## System Overview

The **Autonomous Recruitment Agent** is a microservices-based AI-powered recruitment automation system designed to streamline the entire hiring workflow from resume screening to onboarding.

---

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                          │
│                     (Next.js + React + TypeScript)              │
│  - Dashboard UI  - Candidate Management  - Interview Scheduling │
└────────────────────┬────────────────────────────────────────────┘
                     │ REST API (HTTPS)
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                        API Gateway Layer                        │
│                        (FastAPI + Uvicorn)                      │
│  - Authentication  - Rate Limiting  - Request Validation        │
└─────────┬──────────┬──────────┬──────────┬──────────────────────┘
          │          │          │          │
          │          │          │          │
┌─────────▼──┐ ┌─────▼──┐ ┌────▼────┐ ┌───▼─────────┐
│  Resume    │ │ Matching│ │Schedule │ │  Feedback   │
│  Service   │ │ Service │ │ Service │ │  Service    │
└─────┬──────┘ └────┬────┘ └────┬────┘ └──────┬──────┘
      │             │           │             │
      └─────────────┴───────────┴─────────────┘
                    │
           ┌────────▼─────────┐
           │   AI Agent Layer │
           │  (LangChain +    │
           │   OpenAI GPT)    │
           └────────┬─────────┘
                    │
      ┌─────────────┼─────────────┐
      │             │             │
┌─────▼──────┐ ┌───▼────┐ ┌──────▼────┐
│ PostgreSQL │ │ Redis  │ │   n8n     │
│  Database  │ │ Cache  │ │ Workflows │
└────────────┘ └────────┘ └───────────┘
```

---

## 📦 Component Architecture

### 1. Frontend (Next.js)

**Location:** `/frontend`

**Tech Stack:**
- Next.js 15 (React 19)
- TypeScript
- Tailwind CSS
- Radix UI Components
- React Query (TanStack Query)
- Framer Motion

**Key Features:**
- Server-side rendering (SSR)
- Role-based access control (RBAC)
- Real-time updates via WebSocket
- Responsive design
- Firebase Authentication

**Directory Structure:**
```
frontend/
├── src/
│   ├── app/              # Next.js app router
│   ├── components/       # Reusable UI components
│   │   ├── ui/          # Base UI components
│   │   └── features/    # Feature-specific components
│   ├── hooks/           # Custom React hooks
│   ├── lib/             # Utility libraries
│   ├── services/        # API service clients
│   └── types/           # TypeScript definitions
├── public/              # Static assets
└── package.json
```

---

### 2. Backend (FastAPI)

**Location:** `/backend`

**Tech Stack:**
- FastAPI (Python 3.9+)
- SQLAlchemy (ORM)
- PostgreSQL
- Redis (caching & queuing)
- Celery (background tasks)
- LangChain + OpenAI
- Prometheus (metrics)

**Directory Structure:**
```
backend/
├── agents/              # AI agents
│   ├── resume_analyzer.py
│   └── matcher_agent.py
├── api/                 # API route handlers
│   ├── job_router.py
│   ├── candidate_router.py
│   ├── auth_router.py
│   └── ...
├── services/            # Business logic
│   ├── resume_service.py
│   ├── matching_service.py
│   ├── scheduling_service.py
│   ├── feedback_service.py
│   └── onboarding_service.py
├── workers/             # Background task workers
│   └── tasks.py
├── security/            # Auth & security
├── migrations/          # Database migrations
├── tests/               # Test suites
└── utils/               # Utility functions
```

**API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/resume/analyze` | POST | Upload and parse resume |
| `/resume/match` | POST | Match resumes to job |
| `/interview/schedule` | POST | Schedule interview |
| `/interview/feedback` | POST | Submit feedback |
| `/jobs/create` | POST | Create new job posting |
| `/auth/login` | POST | User authentication |

---

### 3. AI Agent Layer

**Components:**

#### Resume Analyzer Agent
- Extracts structured data from unstructured resumes
- Supports PDF, DOCX, DOC formats
- Uses regex patterns + NLP for entity extraction
- Sentiment analysis on resume content

#### Matching Service Agent
- Semantic matching using sentence transformers
- Embeddings-based similarity scoring
- Threshold-based candidate filtering
- Ranking algorithm with configurable weights

#### Interview Assistant
- Automated scheduling with conflict resolution
- Panel member assignment with load balancing
- Reminder notifications
- No-show detection

**AI Models Used:**
- **OpenAI GPT-4**: Resume summarization, JD generation
- **Sentence Transformers**: Semantic search & matching
- **LangChain**: Agent orchestration & prompt management

---

### 4. Database Schema

**PostgreSQL Tables:**

```sql
-- Core tables
resume_data (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR,
    candidate_name VARCHAR,
    email VARCHAR UNIQUE,
    phone VARCHAR,
    skills TEXT,
    education TEXT,
    ai_score FLOAT,
    interview_status VARCHAR,
    created_at TIMESTAMP
)

jobs (
    id SERIAL PRIMARY KEY,
    title VARCHAR,
    description TEXT,
    requirements TEXT,
    status VARCHAR,
    created_by INT,
    created_at TIMESTAMP
)

interview_schedules (
    id SERIAL PRIMARY KEY,
    candidate_email VARCHAR,
    candidate_name VARCHAR,
    interviewer_id INT,
    scheduled_time TIMESTAMP,
    status VARCHAR,
    feedback_submitted BOOLEAN,
    created_at TIMESTAMP
)

interviewers (
    id SERIAL PRIMARY KEY,
    name VARCHAR,
    email VARCHAR UNIQUE,
    department VARCHAR,
    specialization VARCHAR[],
    availability_hours JSONB
)

feedback (
    id SERIAL PRIMARY KEY,
    interview_id INT REFERENCES interview_schedules(id),
    technical_skills INT,
    communication_skills INT,
    overall_rating INT,
    recommendation VARCHAR,
    detailed_feedback TEXT,
    submitted_at TIMESTAMP
)

users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE,
    firebase_uid VARCHAR UNIQUE,
    role VARCHAR,
    created_at TIMESTAMP
)
```

**Indexes:**
```sql
CREATE INDEX idx_resume_email ON resume_data(email);
CREATE INDEX idx_resume_status ON resume_data(interview_status);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_interview_time ON interview_schedules(scheduled_time);
```

---

### 5. Workflow Engine (n8n)

**Location:** External service (Docker container)

**Purpose:**
- Orchestrate complex multi-step workflows
- Email automation (invitations, reminders, rejections)
- Webhook integrations
- Scheduled task execution

**Key Workflows:**
1. **Resume Screening Workflow**
   - Triggered on resume upload
   - Parse → Score → Notify → Update DB

2. **Interview Scheduling Workflow**
   - Find available slots
   - Send calendar invites
   - Set up reminders

3. **Feedback Collection Workflow**
   - Post-interview kit dispatch
   - Reminder emails
   - Aggregate scores

4. **Onboarding Workflow**
   - Document collection
   - Account creation
   - Welcome emails

---

## 🔄 Data Flow

### Resume Processing Flow

```
User uploads resume
    ↓
FastAPI receives file
    ↓
Background task queued (Celery)
    ↓
Resume Parser extracts text
    ↓
AI Agent extracts entities (name, email, skills)
    ↓
Matching Service scores against JD
    ↓
Score stored in PostgreSQL
    ↓
n8n triggers notification workflow
    ↓
Candidate receives email
```

### Interview Scheduling Flow

```
HR initiates interview schedule
    ↓
FastAPI receives schedule request
    ↓
Scheduling Service checks availability
    ↓
Panel members assigned (load balancing)
    ↓
Calendar slots generated
    ↓
Interview record created in DB
    ↓
n8n sends calendar invites
    ↓
Reminders scheduled
```

---

## 🔐 Security Architecture

### Authentication & Authorization

**Frontend:**
- Firebase Authentication
- JWT token management
- Secure HttpOnly cookies

**Backend:**
- Firebase Admin SDK for token verification
- Role-based access control (RBAC)
- API key authentication for n8n webhooks

**Roles:**
- `admin`: Full system access
- `hr`: Manage jobs, candidates, interviews
- `interviewer`: View schedules, submit feedback
- `candidate`: View own application status

### Data Security

- Passwords: Not stored (Firebase handles auth)
- API Keys: Environment variables only
- Database: SSL connections
- File uploads: Virus scanning (optional)
- Rate limiting: 100 requests/minute per IP

---

## ⚡ Performance Optimizations

### Caching Strategy (Redis)

```python
# Cache frequently accessed data
cache_keys = {
    "interview_status": 300,      # 5 minutes
    "candidate_list": 600,        # 10 minutes
    "job_details": 1800,          # 30 minutes
    "panel_templates": 3600       # 1 hour
}
```

### Database Optimizations

- Connection pooling (SQLAlchemy)
- Indexed columns for fast queries
- Batch inserts for bulk operations
- Query result caching

### Background Processing

- Celery workers for async tasks
- Redis as message broker
- Separate queues for different priority tasks

---

## 📊 Monitoring & Observability

### Metrics (Prometheus)

**Exposed at:** `http://localhost:8000/api/metrics`

**Key Metrics:**
- `http_requests_total`: Total API requests
- `http_request_duration_seconds`: Request latency
- `resume_processing_time`: Time to process resumes
- `active_interviews`: Currently scheduled interviews
- `matching_score_distribution`: Distribution of AI scores

### Logging

**Format:** JSON structured logs

```python
{
    "timestamp": "2024-01-15T10:30:00Z",
    "level": "INFO",
    "service": "resume_service",
    "message": "Resume processed successfully",
    "metadata": {
        "candidate_email": "user@example.com",
        "processing_time_ms": 1250,
        "ai_score": 85.5
    }
}
```

### Health Checks

- `/health`: Basic health check
- `/health/db`: Database connectivity
- `/health/redis`: Redis connectivity

---

## 🚀 Deployment Architecture

### Development Environment

```bash
docker-compose up -d
```

**Containers:**
- `fastapi`: Backend API server
- `postgres`: Database
- `redis`: Cache & queue
- `n8n`: Workflow engine
- `frontend`: Next.js dev server

### Production Environment (Recommended)

**Option 1: Docker Swarm**
```
Load Balancer (Nginx)
    ↓
Backend (3 replicas)
    ↓
PostgreSQL (primary + replica)
Redis Cluster
n8n (standalone)
```

**Option 2: Kubernetes**
```yaml
Deployments:
  - backend-api (3 pods)
  - frontend (2 pods)
  - celery-workers (5 pods)
  - n8n (1 pod)

StatefulSets:
  - postgres
  - redis

Services:
  - LoadBalancer for ingress
  - ClusterIP for internal communication
```

---

## 🔧 Configuration Management

### Environment Variables

**Backend (.env):**
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/recruitment_db

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Services
OPENAI_API_KEY=sk-...

# Firebase
FIREBASE_SERVICE_ACCOUNT_JSON='{...}'
ALLOWED_AUTH_EMAILS=admin@company.com,hr@company.com

# n8n
N8N_WEBHOOK_URL=http://n8n:5678/webhook/

# Monitoring
PROMETHEUS_ENABLED=true
```

**Frontend (.env.local):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
```

---

## 🧪 Testing Strategy

### Test Pyramid

```
              ╱╲
             ╱  ╲  E2E Tests (10%)
            ╱────╲
           ╱      ╲ Integration Tests (30%)
          ╱────────╲
         ╱          ╲ Unit Tests (60%)
        ╱────────────╲
```

**Unit Tests:**
- Individual function testing
- Mocked dependencies
- Fast execution (<1s per test)

**Integration Tests:**
- API endpoint testing
- Database interactions
- External service mocking

**E2E Tests:**
- Full user workflows
- Browser automation (Playwright)
- Staging environment

---

## 📈 Scalability Considerations

### Horizontal Scaling

**Backend:**
- Stateless API servers (scale to N replicas)
- Load balancing with sticky sessions
- Shared Redis for session storage

**Database:**
- Read replicas for heavy read operations
- Connection pooling
- Query optimization

**Workers:**
- Multiple Celery workers
- Task-specific queues
- Auto-scaling based on queue length

### Vertical Scaling

- Increase CPU/RAM for AI model inference
- GPU acceleration for large-scale matching
- SSD storage for database

---

## 🔄 Future Architecture Enhancements

1. **Microservices Split:**
   - Separate services for: Resume, Interview, Feedback, Onboarding
   - API Gateway (Kong/AWS API Gateway)
   - Service mesh (Istio)

2. **Event-Driven Architecture:**
   - Message bus (Kafka/RabbitMQ)
   - Event sourcing for audit trail
   - CQRS pattern

3. **Advanced AI:**
   - Fine-tuned models for resume parsing
   - Multi-modal analysis (video interviews)
   - Bias detection algorithms

4. **Analytics Platform:**
   - Data warehouse (Snowflake)
   - BI dashboards (Metabase)
   - Predictive analytics

---

## 📚 References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [LangChain Documentation](https://python.langchain.com/)
- [PostgreSQL Best Practices](https://wiki.postgresql.org/wiki/Don't_Do_This)
- [n8n Documentation](https://docs.n8n.io/)

---

**Last Updated:** 2024-01-15  
**Version:** 1.0  
**Maintained By:** Development Team

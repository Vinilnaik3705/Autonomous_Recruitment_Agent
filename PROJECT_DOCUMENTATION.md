# Project Documentation: Autonomous Recruitment Agent

## 1. Project Overview
This project is an **Automated Resume Screening and Recruitment System**. It is designed to streamline the HR process by automating resume parsing, job description (JD) matching, candidate ranking, and interview scheduling.

**Key Features:**
- **Resume Parsing:** extract text, names, emails, phones, skills, and education from PDF/DOCX files.
- **AI Analysis:** Uses LLMs (OpenAI via LangChain) to analyze sentiment, summarize profiles, and generate Job Descriptions.
- **Matching Engine:** Ranks candidates based on skills and resume content against a provided JD.
- **Interview Management:** Scheduling, feedback collection, and onboarding workflows.
- **Modern UI:** A reactive web interface for HR professionals to manage the pipeline.

## 2. Technology Stack & Rationale

### Backend: Python (FastAPI)
- **Why Python?** Python is the dominant language for AI, NLP, and Data Processing. Libraries like `PyMuPDF` (parsing), `LangChain` (AI), and `Pandas` (data handling) make it the ideal choice.
- **Why FastAPI?** It is a modern, high-performance web framework for building APIs with Python 3.6+ based on standard Python type hints. It offers automatic OpenAPI documentation (`/docs`) and is faster than Flask/Django for async tasks.

### Frontend: JavaScript (React + Vite)
- **Why React?** The industry standard for building dynamic, interactive user interfaces.
- **Why Vite?** A build tool that provides a faster and leaner development experience than Create React App.
- **Why Tailwind CSS?** A utility-first CSS framework for rapidly building custom designs without leaving your HTML.

### Database: PostgreSQL
- **Why PostgreSQL?** A robust, open-source object-relational database system known for reliability and feature robustness. Ideal for structured data like user profiles, resume metadata, and schedules.

---

## 3. Directory Structure & File Explanations

### Root Directory
| File | Format | Purpose |
|------|--------|---------|
| `README.md` | Markdown | General introduction and setup instructions for the project. |
| `requirements.txt` | Text | Lists Python dependencies (FastAPI, uvicorn, psycopg2, langchain, etc.) for `pip install`. |
| `secrets.toml` / `.example` | TOML | Stores sensitive configuration (Database credentials, OpenAI API keys). TOML is used for its readability and standard usage in Streamlit/Python apps. |
| `test_resume_logic.py` | Python | A unit/integration test script to verify that resume parsing functions (regex for email, skills) work correctly without running the full server. |
| `test_webhook.py` | Python | A utility script to test API/Webhook endpoints manually using `requests`. |
| `migrate_education.py` | Python | A database migration script used to add the `education` column to the `resume_data` table. Kept for record; in production, a migration tool like `alembic` is often used. |
| `app_with_chat.py` (Deleted) | Python | *Legacy:* The original monolithic Streamlit application. Deleted in favor of the modular Client-Server architecture. |

### Backend (`/backend`)
The core logic resides here. It serves as the API provider.

#### Core Files
- **`main.py`**:
    - **What it does:** The entry point of the FastAPI application. It initializes the app, configuring CORS, and maps API routes (endpoints) to service functions.
    - **Key Routes:** `/resume/upload-batch` (Processing), `/resume/match` (Ranking), `/interview/schedule` (Logistics).
    - **Why:** Centralizes the HTTP interface definition.

- **`database.py`**:
    - **What it does:** establishes and manages connections to the PostgreSQL database using `psycopg2`.
    - **Why:** Abstracts DB connection logic so it can be reused across services.

- **`init_db.py`**:
    - **What it does:** Contains SQL `CREATE TABLE` statements to set up the database schema (Users, ResumeFiles, ResumeData, InterviewSchedules, etc.).
    - **Why:** run this once to bootstrap the database.

#### Services (`/backend/services`)
Business logic is separated from the API layer.

- **`resume_service.py`**:
    - **What it does:** The heavy lifter for parsing. Uses `fitz` (PyMuPDF) and Regex to Extract text, emails, phone numbers, and skills from files. Includes logic to save/upsert data to the DB.
    - **Key Logic:** Regex patterns for Indian phone numbers, "Degree" detection for education, and deduplication logic.

- **`matching_service.py`**:
    - **What it does:** Compares parsed resumes against a Job Description. Likely uses vector embeddings or weighted keyword matching to return a ranked list of candidates.

- **`scheduling_service.py`**:
    - **What it does:** Manages calendar integrations (Google Calendar, Zoom) and DB records for interview slots. Handles logistics of setting up meetings.

- **`feedback_service.py`**:
    - **What it does:** Handling submission of interview feedback (ratings, comments) and storing it linked to the candidate.

- **`onboarding_service.py`**:
    - **What it does:** Automates the post-hiring process (emails, checklist initialization).

#### Agents (`/backend/agents`)
AI-specific components.

- **`resume_analyzer.py`**:
    - **What it does:** A wrapper around LangChain and OpenAI.
    - **Functions:**
        - `analyze_sentiment_and_summary`: Sends resume text to GPT-4o-mini to get a professional summary and sentiment score.
        - `generate_job_description`: Uses LLM to create a full JD from brief inputs (Role, Skills, Exp).
    - **Why:** Encapsulates all external AI API calls.

### Frontend (`/frontend`)
The User Interface.

- **`package.json`**:
    - **What it does:** Manifest for the Node.js project. Lists dependencies (`react`, `axios`, `lucide-react`, `tailwindcss`) and scripts (`dev`, `build`).

- **`vite.config.js`**:
    - **What it does:** Configures the Vite build tool. Handles plugins like `@vitejs/plugin-react`.

- **`postcss.config.js` & `tailwind.config.js`**:
    - **What it does:** Configuration for tailwind CSS processing.

#### Source (`/frontend/src`)
- **`main.jsx`**:
    - **What it does:** The JavaScript entry point. Mounts the React application into the DOM (`#root` in `index.html`).

- **`App.jsx`**:
    - **What it does:** The root React component. Currently renders the main `HRScreening` component.

- **`api.js`** (Assumed location based on usage):
    - **What it does:** Centralized API client. Uses `axios` or `fetch` to communicate with the Python backend (e.g., `uploadResumesBatch`, `matchResumes`).

- **`components/HRScreening.jsx`**:
    - **What it does:** The main "Dashboard" component.
    - **Features:**
        - **State Management:** Uses `useState` for resumes, match results, JD text, and UI states (loading).
        - **UI:** A two-column layout for "Uploads" and "Job Description".
        - **Logic:** Handles file selection, calls API endpoints to process batches, generate JDs via AI, and displays the final ranked table of candidates with progress bars for match scores.
    - **Why:** Provides a single, cohesive view for the HR user to perform the screening task.

## 4. Workflows

### 1. Resume Upload & Parsing
1. User drops files in `HRScreening.jsx`.
2. Frontend calls `POST /resume/upload-batch`.
3. Backend (`main.py`) receives files, passes them to `resume_service.py`.
4. `resume_service.py` extracts text and metadata.
5. Data is saved to PostgreSQL (`resume_files`, `resume_data`).

### 2. JD Generation (AI)
1. User enters Role/Skills in "Agent" mode in UI.
2. Frontend calls `/utils/generate-jd`.
3. Backend calls `ResumeAnalyzerAgent.generate_job_description`.
4. LLM returns a formatted JD.
5. UI populates the text area.

### 3. Matching
1. User clicks "Start Screening".
2. Frontend calls `/resume/match` with the JD text.
3. `matching_service.py` calculates similarity scores between the JD and stored resumes.
4. Top results are returned and displayed in the React Table.

---
*Created by Antigravity Agent*

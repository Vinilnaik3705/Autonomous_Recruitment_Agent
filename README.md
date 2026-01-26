# HR Automation Agent Setup

## Prerequisites

*   Python 3.10+
*   PostgreSQL
*   n8n (for orchestration)

## Setup

1.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**
    Create a `secrets.toml` or set environment variables:
    ```toml
    [database]
    name = "resume_analyzer"
    user = "postgres"
    password = "your_password"
    
    [openai]
    api_key = "sk-..."
    ```

3.  **Initialize Database**
    Run this command from the root folder (`automated_res`) to create the necessary tables:
    ```bash
    python -m backend.init_db
    ```

4.  **Run the Backend Server**
    ```bash
    uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
    ```
    The API will be available at `http://127.0.0.1:8000`.
    API Documentation (Swagger UI): `http://127.0.0.1:8000/docs`.

5.  **Run the Frontend**
    Open a new terminal:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```
    Access the UI at logical localhost address (usually `http://localhost:5173`).

## Integration with n8n

Use the **HTTP Request** node in n8n to interact with the agent:

*   **Resume Sentiment Analysis**: `POST /resume/sentiment` (Form-Data: file)
*   **Match Resumes**: `POST /resume/match` (JSON: `{ "jd_text": "...", "top_k": 5 }`)
*   **Schedule Interview**: `POST /interview/schedule`
*   **Onboarding**: `POST /onboarding/initiate`

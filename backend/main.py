import sys
import os

# Add project root to sys.path to allow running this script directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Optional, List
from backend.services.resume_service import parse_resume, save_resume_to_db, save_resumes_batch
from backend.database import get_db_connection
from backend.services.scheduling_service import SchedulingService
from backend.services.feedback_service import FeedbackService
from backend.services.onboarding_service import OnboardingService
from backend.agents.resume_analyzer import ResumeAnalyzerAgent
from backend.services.matching_service import MatchingService
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="HR Automation Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
scheduler = SchedulingService()
feedback_service = FeedbackService()
onboarding_service = OnboardingService()
resume_agent = ResumeAnalyzerAgent()
matcher_service = MatchingService()

def process_batch_files(files_data: List[Dict], user_id: int):
    """Background task to process files and save to DB."""
    try:
        # files_data is a list of {"filename": str, "content": bytes}
        parsed_data = []
        for f in files_data:
            try:
                data = parse_resume(f['content'], f['filename'])
                parsed_data.append(data)
            except Exception as e:
                print(f"Error parsing {f['filename']}: {e}")
        
        if parsed_data:
            save_resumes_batch(parsed_data, user_id)
            print(f"Values saved for batch of {len(parsed_data)} files")
            
    except Exception as e:
        print(f"Batch processing failed: {e}")

# --- Phase 2: Resume Screening ---
@app.post("/resume/upload-batch")
async def upload_resume_batch(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...), user_id: int = 1):
    try:
        # Read files into memory (careful with large batches, but 50 files * 1MB = 50MB is fine)
        # If files are too large, we should save to disk first. Assuming controlled batch size from frontend.
        files_data = []
        for file in files:
            content = await file.read()
            files_data.append({"filename": file.filename, "content": content})
        
        background_tasks.add_task(process_batch_files, files_data, user_id)
        
        return {"status": "processing", "message": f"Received {len(files)} files for processing in background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resume/analyze")
async def analyze_resume(file: UploadFile = File(...), user_id: int = 1):
    try:
        content = await file.read()
        data = parse_resume(content, file.filename)
        file_id = save_resume_to_db(data, user_id)
        return {"status": "success", "file_id": file_id, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resume/sentiment")
async def resume_sentiment(file: UploadFile = File(...)):
    try:
        content = await file.read()
        data = parse_resume(content, file.filename)
        analysis = resume_agent.analyze_sentiment_and_summary(data['raw_text'])
        return {"filename": file.filename, "analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SentimentTextRequest(BaseModel):
    resume_text: str

@app.post("/resume/sentiment-text")
def sentiment_text(req: SentimentTextRequest):
    try:
        analysis = resume_agent.analyze_sentiment_and_summary(req.resume_text)
        return {"status": "success", "analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/utils/extract-text")
async def extract_text_from_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        # reusing parse_resume to extract text
        data = parse_resume(content, file.filename)
        return {"filename": file.filename, "text": data['raw_text']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class GenerateJDRequest(BaseModel):
    role: str
    experience: str
    skills: str

@app.post("/utils/generate-jd")
async def generate_jd_endpoint(req: GenerateJDRequest):
    try:
        jd_text = resume_agent.generate_job_description(req.role, req.experience, req.skills)
        return {"jd_text": jd_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/utils/reset")
async def reset_database():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE resume_data, resume_files CASCADE;")
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Database reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class MatchRequest(BaseModel):
    jd_text: str
    top_k: int = 5

@app.post("/resume/match")
def match_resumes_to_jd(req: MatchRequest):
    try:
        results = matcher_service.match_resumes(req.jd_text, req.top_k)
        return {"matches": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Phase 3: Scheduling ---
class ScheduleRequest(BaseModel):
    candidate_email: str
    candidate_name: str
    interviewer_id: int
    slot_iso: str

@app.post("/interview/schedule")
def schedule_interview(req: ScheduleRequest):
    try:
        # Construct dict expected by service
        candidate_data = {"email": req.candidate_email, "name": req.candidate_name}
        interview_id = scheduler.schedule_interview(candidate_data, req.interviewer_id, req.slot_iso)
        return {"status": "scheduled", "interview_id": interview_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/interview/availability/{interviewer_id}")
def get_availability(interviewer_id: int, date: str):
    return scheduler.get_availability(interviewer_id, date)

# --- Phase 4: Feedback ---
class FeedbackRequest(BaseModel):
    interview_id: int
    technical_skills: int
    communication_skills: int
    overall_rating: int
    recommendation: str
    detailed_feedback: str

@app.post("/interview/feedback")
def submit_feedback(req: FeedbackRequest):
    try:
        feedback_service.submit_feedback(req.interview_id, req.model_dump())
        return {"status": "submitted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Phase 5: Onboarding ---
class OnboardingRequest(BaseModel):
    candidate_email: str
    role: str
    start_date: str
    salary: str

@app.post("/onboarding/initiate")
def initiate_onboarding(req: OnboardingRequest):
    try:
        success = onboarding_service.initiate_onboarding(req.candidate_email, req.model_dump())
        if success:
            return {"status": "onboarding_started"}
        else:
            raise HTTPException(status_code=404, detail="Candidate not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Set PYTHONPATH for reload subprocesses to find 'backend' module
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.environ["PYTHONPATH"] = project_root + os.pathsep + os.environ.get("PYTHONPATH", "")

    # Run with reload enabled
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

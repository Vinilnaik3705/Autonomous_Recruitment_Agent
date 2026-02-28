from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from backend.database import get_db_connection
import uuid
import os
import hashlib

router = APIRouter(prefix="/jobs", tags=["Jobs"])

class JobDescriptionCreate(BaseModel):
    title: str
    description: str
    required_skills: str
    min_experience: int = 0
    max_experience: int = 0

def generate_jd_hash(title: str, description: str, required_skills: str) -> str:
    """Generate deterministic job_id from JD content to prevent duplicates."""
    jd_content = f"{title.strip().lower()}|{description.strip().lower()}|{required_skills.strip().lower()}"
    hash_obj = hashlib.sha256(jd_content.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()[:12].upper()
    return f"JOB-{hash_hex}"

@router.post("/create")
def create_job_description(job: JobDescriptionCreate):
    conn = get_db_connection()
    try:
        # Generate deterministic job_id from JD content
        job_id = generate_jd_hash(job.title, job.description, job.required_skills)
        
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if this exact JD already exists
            cur.execute("""
                SELECT job_id FROM job_descriptions WHERE job_id = %s;
            """, (job_id,))
            existing = cur.fetchone()
            
            if existing:
                # Same JD already exists, return existing job_id
                print(f"✓ Reusing existing job_id: {job_id} (same JD detected)")
                return {"status": "success", "job_id": job_id, "reused": True}
            
            # Insert new JD
            cur.execute("""
                INSERT INTO job_descriptions (job_id, title, description, required_skills, min_experience, max_experience)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING job_id;
            """, (job_id, job.title, job.description, job.required_skills, job.min_experience, job.max_experience))
            result = cur.fetchone()
            conn.commit()
            print(f"✓ Created new job_id: {job_id}")
            return {"status": "success", "job_id": result['job_id'], "reused": False}
    except Exception as e:
        conn.rollback()
        print(f"CRITICAL ERROR in create_job_description: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")
    finally:
        conn.close()

from fastapi import UploadFile, File, Form, Depends
import httpx

@router.post("/n8n-proxy")
async def proxy_n8n_resume_upload(
    file: UploadFile = File(...),
    jobId: str = Form("JOB-001")
):
    """
    Proxies single file upload to n8n.
    """
    # Using production webhook (works when workflow is activated)
    N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/resume-upload-atomic")
    
    print(f"\n{'='*60}")
    print(f"📤 PROXY REQUEST TO N8N")
    print(f"{'='*60}")
    print(f"File: {file.filename}")
    print(f"Content-Type: {file.content_type}")
    print(f"Job ID: {jobId}")
    print(f"Target URL: {N8N_WEBHOOK_URL}")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Read file content
            file_content = await file.read()
            print(f"File size: {len(file_content)} bytes")

            file_hash = hashlib.sha256(file_content).hexdigest()

            conn = None
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM resume_files WHERE session_id = %s AND file_hash = %s LIMIT 1",
                        (jobId, file_hash)
                    )
                    exists = cur.fetchone()

                    if exists:
                        print("⚠️ Duplicate resume detected. Skipping upload and processing.")
                        return {
                            "success": True,
                            "duplicate": True,
                            "message": "Duplicate resume detected. Upload ignored.",
                            "job_id": jobId
                        }

                    # Persist file to disk and log metadata for resume_files tracking
                    upload_dir = os.environ.get("RESUME_UPLOAD_DIR", "uploads/resumes")
                    os.makedirs(upload_dir, exist_ok=True)
                    safe_name = f"{jobId}_{uuid.uuid4().hex}_{file.filename}"
                    file_path = os.path.join(upload_dir, safe_name)
                    with open(file_path, "wb") as f:
                        f.write(file_content)

                    cur.execute(
                        """
                        INSERT INTO resume_files (user_id, filename, file_size, file_type, file_hash, processed, session_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (session_id, file_hash) DO NOTHING
                        """,
                        (None, safe_name, len(file_content), file.content_type or "application/pdf", file_hash, True, jobId)
                    )
                conn.commit()
            except Exception as db_err:
                if conn:
                    conn.rollback()
                print(f"⚠️ Failed to log resume_files: {db_err}")
            finally:
                if conn:
                    conn.close()
            
            # N8N expects files with field name 'data' for binary processing
            files = [
                ('data', (file.filename, file_content, file.content_type or 'application/pdf'))
            ]
            data = {
                'jobId': jobId,
                'fileName': file.filename
            }
            
            print(f"Sending request to n8n...")
            # Forward to n8n
            response = await client.post(N8N_WEBHOOK_URL, files=files, data=data)
            
            print(f"✅ Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body Preview: {response.text[:500]}")
            print(f"{'='*60}\n")
            
            if response.status_code != 200:
                print(f"❌ n8n Error [{response.status_code}]: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"n8n Error: {response.text}"
                )
            
            # Check if response is JSON
            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type:
                print(f"⚠️ Warning: n8n returned non-JSON response (Content-Type: {content_type})")
                print(f"Full response: {response.text}")
                # Return a success response anyway if status is 200
                return {
                    "success": True,
                    "message": "Resume uploaded to n8n",
                    "n8n_response": response.text[:200]
                }
            
            try:
                return response.json()
            except Exception as json_error:
                print(f"❌ JSON Parse Error: {json_error}")
                print(f"Response text: {response.text}")
                # Return success if we got 200, even if JSON parsing failed
                return {
                    "success": True,
                    "message": "Resume uploaded but response parsing failed",
                    "raw_response": response.text[:200]
                }
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        print(f"❌ Proxy Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Proxy Error: {str(e)}")

@router.post("/batch-screen")
async def batch_screen_resumes(
    files: List[UploadFile] = File(...),
    jobId: str = Form(...)
):
    """
    Batch process multiple resumes with embeddings-based scoring.
    Uses Sentence Transformers for semantic similarity matching.
    Threshold: 35/100 for shortlisting.
    """
    from backend.services.resume_service import extract_text_and_links_from_pdf_stream
    from backend.database import close_db
    import json
    
    print(f"\n{'='*60}")
    print(f"📊 BATCH RESUME SCREENING")
    print(f"{'='*60}")
    print(f"Job ID: {jobId}")
    print(f"Number of files: {len(files)}")
    
    conn = None
    try:
        conn = get_db_connection()
        # Get job description
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM job_descriptions WHERE job_id = %s",
                (jobId,)
            )
            job = cur.fetchone()
            
            if not job:
                raise HTTPException(status_code=404, detail=f"Job {jobId} not found")
        
        job_description = f"{job['title']}\n{job['description']}\nRequired Skills: {job['required_skills']}"
        print(f"Job: {job['title']}")
        
        # Extract text from all PDFs
        resume_data_list = []
        for file in files:
            try:
                print(f"Processing: {file.filename}")
                file_content = await file.read()
                
                # Extract PDF text
                resume_text, _ = extract_text_and_links_from_pdf_stream(file_content)
                
                # Use proper parsing functions for accurate extraction
                from backend.services.resume_service import extract_name, extract_email, extract_contact_number, extract_skills as extract_resume_skills
                
                name = extract_name(resume_text) or "Unknown"
                email = extract_email(resume_text) or ""
                phone = extract_contact_number(resume_text) or ""
                skills = extract_resume_skills(resume_text)
                
                resume_data_list.append({
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'resume_text': resume_text,
                    'skills': skills,
                    'filename': file.filename
                })
                
            except Exception as e:
                print(f"Error processing {file.filename}: {e}")
                continue
        
        if not resume_data_list:
            raise HTTPException(status_code=400, detail="No valid resumes could be processed")
        
        # Score all resumes using embeddings
        print(f"\n🧠 Scoring {len(resume_data_list)} resumes with embeddings...")
        from backend.services.matching_service import get_matching_service
        matching_service = get_matching_service()
        scored_results = matching_service.score_new_resumes_for_job(
            job_description=job_description,
            resume_data_list=resume_data_list,
            threshold=35.0  # Threshold score for shortlisting
        )
        
        # Save to all three tables with UPSERT to prevent duplicates
        print(f"\n💾 Saving to database with duplicate prevention...")
        saved_candidates = []
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for idx, result in enumerate(scored_results):
                # Check if candidate already exists for this job
                cur.execute("""
                    SELECT id FROM resume_data 
                    WHERE job_id = %s AND email = %s;
                """, (jobId, result['email']))
                existing_resume = cur.fetchone()
                
                if existing_resume:
                    print(f"  ↻ Updating existing candidate: {result['candidate_name']} ({result['email']})")
                    file_id = None  # Don't create new file entry for existing candidate
                    
                    # Update existing resume_data with new score
                    cur.execute("""
                        UPDATE resume_data 
                        SET candidate_name = %s, phone = %s, skills = %s, 
                            ai_score = %s, ai_summary = %s
                        WHERE id = %s
                        RETURNING id;
                    """, (
                        result['candidate_name'],
                        result['phone'],
                        json.dumps(result['skills']),
                        result['score'],
                        f"Match Score: {result['score']:.1f}/100",
                        existing_resume['id']
                    ))
                    resume_data_id = cur.fetchone()['id']
                else:
                    print(f"  ✓ Adding new candidate: {result['candidate_name']} ({result['email']})")
                    
                    # 1. Save to resume_files (file metadata) - only for new candidates
                    # Calculate file size from skills and other data (resume_text not stored in DB)
                    file_size = len(json.dumps({
                        'name': result['candidate_name'],
                        'email': result['email'],
                        'skills': result['skills']
                    }).encode('utf-8'))
                    
                    cur.execute("""
                        INSERT INTO resume_files (filename, file_size, file_type, processed, session_id)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (
                        result.get('filename', 'unknown.pdf'),
                        file_size,
                        'application/pdf',
                        True,
                        jobId
                    ))
                    file_id = cur.fetchone()['id']
                    
                    # 2. Insert new resume_data (parsed content)
                    cur.execute("""
                        INSERT INTO resume_data 
                        (job_id, candidate_name, email, phone, skills, ai_score, ai_summary)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (
                        jobId,
                        result['candidate_name'],
                        result['email'],
                        result['phone'],
                        json.dumps(result['skills']),
                        result['score'],
                        f"Match Score: {result['score']:.1f}/100"
                    ))
                    resume_data_id = cur.fetchone()['id']
                
                # 3. Save to candidates (workflow tracking)
                cur.execute("""
                    INSERT INTO candidates 
                    (name, email, phone, file_name, skills, match_score, resume_shortlisted)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (email) DO UPDATE SET
                        match_score = EXCLUDED.match_score,
                        resume_shortlisted = EXCLUDED.resume_shortlisted,
                        skills = EXCLUDED.skills
                    RETURNING id;
                """, (
                    result['candidate_name'],
                    result['email'],
                    result['phone'],
                    result.get('filename', 'unknown.pdf'),
                    ', '.join(result['skills']) if isinstance(result['skills'], list) else str(result['skills']),
                    result['score'],
                    result['shortlisted']
                ))
                candidate_id = cur.fetchone()['id']
                
                saved_candidates.append({
                    'candidate_id': candidate_id,
                    'resume_data_id': resume_data_id,
                    'file_id': file_id,
                    'candidate_name': result['candidate_name'],
                    'email': result['email'],
                    'phone': result['phone'],
                    'skills': ', '.join(result['skills']) if isinstance(result['skills'], list) else result['skills'],
                    'score': result['score'],
                    'shortlisted': result['shortlisted'],
                    'threshold': result['threshold']
                })
            
            conn.commit()
        
        print(f"✅ Saved {len(saved_candidates)} candidates")
        
        # Auto-trigger interview scheduling for shortlisted candidates
        shortlisted = [c for c in saved_candidates if c['shortlisted']]
        if shortlisted:
            print(f"\n📅 Auto-triggering interview scheduling for {len(shortlisted)} shortlisted candidates...")
            
            # 🔧 FIX: Filter out candidates who already have scheduled interviews
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT candidate_email FROM interview_schedules WHERE status = 'scheduled'")
                already_scheduled_emails = {row[0] for row in cur.fetchall()}
            
            # Filter shortlisted candidates to exclude those already scheduled
            candidates_to_schedule = [c for c in shortlisted if c['email'] not in already_scheduled_emails]
            
            if not candidates_to_schedule:
                print(f"⚠️ All {len(shortlisted)} shortlisted candidates already have interviews scheduled. Skipping.")
            else:
                print(f"✓ {len(candidates_to_schedule)} out of {len(shortlisted)} candidates need scheduling (filtering {len(already_scheduled_emails)} duplicates)")
                
                try:
                    import requests
                    N8N_SCHEDULE_URL = os.environ.get("N8N_SCHEDULE_WEBHOOK", "http://localhost:5678/webhook/schedule-interviews")
                    response = requests.post(N8N_SCHEDULE_URL, json={
                        'job_id': jobId,
                        'shortlisted_candidates': candidates_to_schedule
                    }, timeout=30.0)
                    print(f"✅ Interview scheduling triggered: {response.status_code}")
                except Exception as e:
                    print(f"⚠️ Interview scheduling trigger failed (non-critical): {e}")
        
        print(f"{'='*60}\n")
        
        return {
            'success': True,
            'job_id': jobId,
            'total_processed': len(saved_candidates),
            'shortlisted_count': len(shortlisted),
            'rejected_count': sum(1 for c in saved_candidates if not c['shortlisted']),
            'threshold': 35.0,
            'candidates': saved_candidates,
            'interviews_scheduled': len(shortlisted) > 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error in batch screening: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Batch screening error: {str(e)}")
    finally:
        close_db(conn)

@router.get("/results/{job_id}")
def get_screening_results(job_id: str):
    """
    Fetch screening results for a given job_id directly from the database.
    Used by the frontend to poll for results after uploading resumes via n8n,
    without re-triggering the n8n screening webhook each time.
    """
    from backend.database import close_db
    conn = None
    try:
        conn = get_db_connection()
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT ON (email)
                    id, job_id, candidate_name, email, phone,
                    skills, ai_score, interview_status,
                    resume_url, created_at
                FROM resume_data
                WHERE job_id = %s
                ORDER BY email, ai_score DESC NULLS LAST;
            """, (job_id,))
            rows = cur.fetchall()

        # Sort by score descending after dedup
        rows = sorted(rows, key=lambda r: float(r["ai_score"] or 0), reverse=True)

        results = []
        for r in rows:
            results.append({
                "candidate_name": r["candidate_name"] or "",
                "email": r["email"] or "",
                "phone": r["phone"] or "",
                "skills": r["skills"] or "",
                "match_score": float(r["ai_score"] or 0),
                "file_name": r["resume_url"] or "",   # resume_url used as display name
                "status": r["interview_status"] or "PENDING",
                "ai_summary": "",                      # column may not exist in older DBs
            })

        return {"job_id": job_id, "count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db(conn)



@router.get("/list")
def list_jobs():
    from backend.database import close_db
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT job_id, title, description, required_skills, min_experience, max_experience, created_at FROM job_descriptions_readable ORDER BY created_at DESC;")
            jobs = cur.fetchall()
            return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db(conn)

@router.get("/candidates")
def list_candidates():
    """Get all candidates from the candidates table with their workflow status."""
    from backend.database import close_db
    conn = None
    try:
        conn = get_db_connection()
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    id, name, email, phone, skills, 
                    match_score, resume_shortlisted,
                    oa_date, oa_practice_sent, oa_original_sent, oa_score,
                    reminder_2d_sent, reminder_1d_sent, reminder_1h_sent,
                    created_at
                FROM candidates 
                ORDER BY match_score DESC NULLS LAST, created_at DESC;
            """)
            candidates = cur.fetchall()
            return {
                "total": len(candidates),
                "shortlisted": sum(1 for c in candidates if c['resume_shortlisted']),
                "candidates": candidates
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db(conn)

@router.get("/database-status")
def get_database_status():
    """Get comprehensive database status across all tables."""
    from backend.database import close_db
    conn = None
    try:
        conn = get_db_connection()
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Count in each table
            cur.execute("SELECT COUNT(*) as count FROM job_descriptions")
            jobs_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM resume_files")
            files_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM resume_data")
            resume_data_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM candidates")
            candidates_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM candidates WHERE resume_shortlisted = TRUE")
            shortlisted_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM interview_schedules")
            interviews_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM interview_feedback")
            feedback_count = cur.fetchone()['count']
            
            return {
                "job_descriptions": jobs_count,
                "resume_files": files_count,
                "resume_data": resume_data_count,
                "candidates": candidates_count,
                "shortlisted_candidates": shortlisted_count,
                "interview_schedules": interviews_count,
                "interview_feedback": feedback_count,
                "message": "All tables are properly utilized"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        close_db(conn)


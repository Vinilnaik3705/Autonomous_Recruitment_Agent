from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.database import get_db_connection
import uuid
import os
import hashlib
import asyncio
from backend.phase_logger import log_phase_completion

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _send_shortlisted_resume_email(resume_data_id: int, candidate_name: str, candidate_email: str) -> None:
    """Send the resume-shortlisted email and mark the DB row as notified."""
    try:
        from backend.routers.email_router import EmailRequest, get_resume_shortlisted_email, send_email_via_smtp

        template = get_resume_shortlisted_email(
            EmailRequest(candidate_email=candidate_email, candidate_name=candidate_name)
        )
        if template.get("skipped"):
            print(f"⚠️ Skipping shortlist email for {candidate_email}: missing candidate data")
            return

        success, message = send_email_via_smtp(
            recipient_email=template["recipient_email"],
            recipient_name=template.get("recipient_name", candidate_name),
            subject=template["subject"],
            body=template["body"],
            is_html=True,
        )
        if not success:
            print(f"⚠️ Shortlist email failed for {candidate_email}: {message}")
            return

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE resume_data SET email_sent = TRUE WHERE id = %s;",
                    (resume_data_id,),
                )
                conn.commit()
        finally:
            conn.close()

        print(f"✅ Shortlist email sent to {candidate_email}")
    except Exception as exc:
        print(f"⚠️ Error sending shortlist email for {candidate_email}: {exc}")

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

import httpx


def _candidate_n8n_bases(primary_url: str) -> list[str]:
    """Return deduplicated n8n base URLs that work across local + docker runs."""
    editor_base = os.environ.get("N8N_EDITOR_BASE_URL")
    primary_base = primary_url.split("/webhook")[0].rstrip("/")
    candidates = [
        editor_base,
        primary_base,
        "http://localhost:5678",
        "http://127.0.0.1:5678",
        "http://host.docker.internal:5678",
        "http://n8n:5678",
    ]

    seen = set()
    ordered = []
    for base in candidates:
        if base and base not in seen:
            seen.add(base)
            ordered.append(base.rstrip("/"))
    return ordered


def _candidate_webhook_urls(primary_url: str) -> list[str]:
    """Build deduplicated webhook candidates preserving original webhook path."""
    webhook_suffix = primary_url.split(":5678")[-1]
    urls = [primary_url]
    for base in _candidate_n8n_bases(primary_url):
        if "/webhook" in webhook_suffix:
            urls.append(f"{base}{webhook_suffix}")

    seen = set()
    ordered = []
    for url in urls:
        u = (url or "").rstrip("/")
        if u and u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def _parse_resume_payload(file_name: str, file_content: bytes) -> Dict[str, Any]:
    from backend.services.resume_service import (
        extract_text_and_links_from_pdf_stream,
        extract_name,
        extract_email,
        extract_contact_number,
        extract_skills as extract_resume_skills,
    )

    resume_text, _ = extract_text_and_links_from_pdf_stream(file_content)
    return {
        'name': extract_name(resume_text) or "Unknown",
        'email': extract_email(resume_text) or "",
        'phone': extract_contact_number(resume_text) or "",
        'skills': extract_resume_skills(resume_text),
        'resume_text': resume_text,
        'filename': file_name,
    }


async def _extract_resume_payloads(files: List[UploadFile], concurrency: int = 4) -> List[Dict[str, Any]]:
    if not files:
        return []

    semaphore = asyncio.Semaphore(max(1, min(concurrency, len(files))))

    async def process_file(file: UploadFile):
        try:
            file_content = await file.read()
            async with semaphore:
                return await asyncio.to_thread(_parse_resume_payload, file.filename, file_content)
        except Exception as exc:
            return exc

    parsed = await asyncio.gather(*(process_file(file) for file in files), return_exceptions=False)
    valid_payloads: List[Dict[str, Any]] = []
    for idx, result in enumerate(parsed):
        if isinstance(result, Exception):
            print(f"Error processing {files[idx].filename}: {result}")
            continue
        valid_payloads.append(result)

    return valid_payloads

@router.get("/health")
async def check_n8n_health():
    """
    Health check endpoint - verifies N8N is reachable.
    Frontend calls this before attempting uploads.
    """
    webhook_url = os.environ.get("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/resume-upload-atomic")
    editor_base = os.environ.get("N8N_EDITOR_BASE_URL")
    env_base = (editor_base or webhook_url.split("/webhook")[0]).rstrip("/")

    # Probe multiple common hosts to support mixed local + docker runs.
    # This avoids false "unhealthy" results when env points to a host only
    # reachable from one runtime (container vs host machine).
    candidate_bases = [
        env_base,
        "http://localhost:5678",
        "http://127.0.0.1:5678",
        "http://host.docker.internal:5678",
        "http://n8n:5678",
    ]
    seen = set()
    bases_to_probe = []
    for base in candidate_bases:
        if base and base not in seen:
            seen.add(base)
            bases_to_probe.append(base)

    # n8n versions/configs differ: some return 401/403/404 on API endpoints
    # even when the service is running. We consider it healthy if host responds < 500.
    probe_paths = ["/healthz", "/api/v1/me", "/"]
    errors = []

    async with httpx.AsyncClient(timeout=5.0) as client:
        for base in bases_to_probe:
            for path in probe_paths:
                probe_url = f"{base}{path}"
                try:
                    response = await client.get(probe_url, follow_redirects=True)
                    if response.status_code < 500:
                        return {
                            "status": "healthy",
                            "n8n": "running",
                            "base": base,
                            "probe": probe_url,
                            "statusCode": response.status_code,
                        }
                except Exception as e:
                    errors.append(f"{probe_url}: {str(e)}")

    return {
        "status": "unhealthy",
        "n8n": "unreachable",
        "base": env_base,
        "probed_bases": bases_to_probe,
        "errors": errors,
    }

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
    webhook_candidates = _candidate_webhook_urls(N8N_WEBHOOK_URL)
    
    print(f"\n{'='*60}")
    print(f"📤 PROXY REQUEST TO N8N")
    print(f"{'='*60}")
    print(f"File: {file.filename}")
    print(f"Content-Type: {file.content_type}")
    print(f"Job ID: {jobId}")
    print(f"Target URL: {N8N_WEBHOOK_URL}")
    print(f"Candidates: {webhook_candidates}")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Read file content
            file_content = await file.read()
            print(f"File size: {len(file_content)} bytes")
            
            # N8N expects files with field name 'data' for binary processing
            files = [
                ('data', (file.filename, file_content, file.content_type or 'application/pdf'))
            ]
            data = {
                'jobId': jobId,
                'fileName': file.filename
            }
            
            print(f"Sending request to n8n...")
            response = None
            attempt_errors = []

            for webhook_url in webhook_candidates:
                try:
                    response = await client.post(webhook_url, files=files, data=data)
                    print(f"Tried: {webhook_url} -> {response.status_code}")

                    if response.status_code == 200:
                        break

                    attempt_errors.append(f"{webhook_url} -> HTTP {response.status_code}")
                except Exception as req_exc:
                    attempt_errors.append(f"{webhook_url} -> {str(req_exc)}")

            if response is None:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "message": "Unable to reach n8n webhook from backend",
                        "attempts": attempt_errors,
                    },
                )

            print(f"✅ Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body Preview: {response.text[:500]}")
            print(f"{'='*60}\n")

            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "message": "n8n upload webhook did not return HTTP 200",
                        "attempts": attempt_errors,
                        "response_preview": response.text[:300],
                    },
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Proxy Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Proxy Error: {str(e)}")


@router.post("/start-screening-proxy")
async def proxy_start_screening(background_tasks: BackgroundTasks, jobId: str = Form(...)):
    """Proxy screening trigger through FastAPI and fallback to schedule webhook when needed."""
    N8N_SCREEN_URL = os.environ.get("N8N_START_SCREENING_WEBHOOK", "http://localhost:5678/webhook/start-screening")
    N8N_SCHEDULE_URL = (
        os.environ.get("N8N_SCHEDULE_WEBHOOK")
        or os.environ.get("N8N_SCHEDULE_WEBHOOK_URL")
        or "http://localhost:5678/webhook/schedule-interviews"
    )
    webhook_candidates = _candidate_webhook_urls(N8N_SCREEN_URL)
    for url in _candidate_webhook_urls(N8N_SCHEDULE_URL):
        if url not in webhook_candidates:
            webhook_candidates.append(url)

    print(f"\n{'='*60}")
    print(f"🚀 PROXY REQUEST TO N8N START SCREENING")
    print(f"{'='*60}")
    print(f"Job ID: {jobId}")
    print(f"Target URL: {N8N_SCREEN_URL}")
    print(f"Candidates: {webhook_candidates}")

    try:
        shortlisted_candidates = []
        conn = get_db_connection()
        try:
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, candidate_name, email, phone, skills, ai_score, email_sent
                    FROM resume_data
                    WHERE job_id = %s AND ai_score >= 35
                    ORDER BY ai_score DESC;
                    """,
                    (jobId,),
                )
                rows = cur.fetchall() or []
                cur.execute(
                    """
                    SELECT DISTINCT LOWER(TRIM(candidate_email)) AS candidate_email
                    FROM interview_schedules
                    WHERE status = 'scheduled' AND candidate_email IS NOT NULL;
                    """
                )
                already_scheduled_emails = {
                    (row.get("candidate_email") or "").strip().lower()
                    for row in (cur.fetchall() or [])
                    if (row.get("candidate_email") or "").strip()
                }

                seen_emails = set()
                for row in rows:
                    normalized_email = (row.get("email") or "").strip().lower()
                    if not normalized_email:
                        continue
                    if normalized_email in seen_emails:
                        continue
                    seen_emails.add(normalized_email)

                    skills = row.get("skills")
                    if isinstance(skills, str):
                        skills_text = skills
                    elif skills is None:
                        skills_text = ""
                    else:
                        skills_text = str(skills)

                    shortlisted_candidates.append(
                        {
                            "resume_data_id": row.get("id"),
                            "candidate_name": row.get("candidate_name") or "Candidate",
                            "email": row.get("email") or "",
                            "phone": row.get("phone") or "",
                            "skills": skills_text,
                            "score": float(row.get("ai_score") or 0),
                            "shortlisted": True,
                            "email_sent": bool(row.get("email_sent")),
                            "already_scheduled": normalized_email in already_scheduled_emails,
                        }
                    )
        finally:
            conn.close()

        # Ensure shortlisted email is sent for n8n-driven flow as well.
        for candidate in shortlisted_candidates:
            if candidate.get("email_sent"):
                continue
            if not candidate.get("email"):
                continue
            if not candidate.get("resume_data_id"):
                continue
            background_tasks.add_task(
                _send_shortlisted_resume_email,
                candidate.get("resume_data_id"),
                candidate.get("candidate_name") or "Candidate",
                candidate.get("email"),
            )

        # Do not schedule interviews again for candidates who already have one.
        candidates_to_schedule = [
            {
                "candidate_name": c.get("candidate_name") or "Candidate",
                "email": c.get("email") or "",
                "phone": c.get("phone") or "",
                "skills": c.get("skills") or "",
                "score": float(c.get("score") or 0),
                "shortlisted": True,
            }
            for c in shortlisted_candidates
            if not c.get("already_scheduled")
        ]

        payload = {
            "jobId": jobId,
            "job_id": jobId,
            "shortlisted_candidates": candidates_to_schedule,
        }

        if not candidates_to_schedule:
            return {
                "success": True,
                "message": "No new shortlisted candidates to schedule.",
                "job_id": jobId,
                "shortlisted_candidates": 0,
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = None
            attempt_errors = []
            for webhook_url in webhook_candidates:
                try:
                    response = await client.post(webhook_url, json=payload)
                    print(f"Tried: {webhook_url} -> {response.status_code}")
                    if response.status_code < 400:
                        break
                    attempt_errors.append(f"{webhook_url} -> HTTP {response.status_code}")
                except Exception as req_exc:
                    attempt_errors.append(f"{webhook_url} -> {str(req_exc)}")

            if response is None:
                return {
                    "success": False,
                    "message": "No screening webhook reachable; trigger skipped",
                    "job_id": jobId,
                    "shortlisted_candidates": len(candidates_to_schedule),
                    "attempts": attempt_errors,
                }

            print(f"✅ Screening trigger response status: {response.status_code}")
            print(f"Response preview: {response.text[:500]}")

            if response.status_code >= 400:
                return {
                    "success": False,
                    "message": "Screening webhook returned an error; trigger skipped",
                    "job_id": jobId,
                    "shortlisted_candidates": len(candidates_to_schedule),
                    "attempts": attempt_errors,
                    "response_preview": response.text[:300],
                }

            if "application/json" in response.headers.get("content-type", ""):
                try:
                    return response.json()
                except Exception:
                    pass

            return {
                "success": True,
                "message": "Screening triggered successfully",
                "status_code": response.status_code,
                "shortlisted_candidates": len(candidates_to_schedule),
                "raw_response": response.text[:200],
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Screening proxy error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Proxy Error: {str(e)}")

@router.post("/batch-screen")
async def batch_screen_resumes(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    jobId: str = Form(...)
):
    """
    Batch process multiple resumes with embeddings-based scoring.
    Uses Sentence Transformers for semantic similarity matching.
    Threshold: 35/100 for shortlisting.
    """
    import json
    
    print(f"\n{'='*60}")
    print(f"📊 BATCH RESUME SCREENING")
    print(f"{'='*60}")
    print(f"Job ID: {jobId}")
    print(f"Number of files: {len(files)}")
    
    conn = get_db_connection()
    try:
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
        
        # Extract text from all resumes with bounded concurrency.
        resume_data_list = await _extract_resume_payloads(files, concurrency=4)
        
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
            existing_resume_by_email = {}
            candidate_emails = list({
                (r.get('email') or '').strip().lower()
                for r in scored_results
                if (r.get('email') or '').strip()
            })

            if candidate_emails:
                cur.execute(
                    """
                    SELECT id, email, email_sent
                    FROM resume_data
                    WHERE job_id = %s AND LOWER(email) = ANY(%s);
                    """,
                    (jobId, candidate_emails),
                )
                existing_resume_by_email = {
                    (row['email'] or '').strip().lower(): row
                    for row in cur.fetchall()
                    if (row.get('email') or '').strip()
                }

            for idx, result in enumerate(scored_results):
                normalized_email = (result.get('email') or '').strip().lower()
                existing_resume = existing_resume_by_email.get(normalized_email) if normalized_email else None
                
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
                    email_sent = bool(existing_resume.get('email_sent'))
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
                    email_sent = False

                    if normalized_email:
                        existing_resume_by_email[normalized_email] = {
                            'id': resume_data_id,
                            'email_sent': email_sent,
                        }
                
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
                    'threshold': result['threshold'],
                    'email_sent': email_sent,
                })
            
            conn.commit()

        shortlisted = [c for c in saved_candidates if c['shortlisted']]

        for candidate in shortlisted:
            if candidate.get('email_sent'):
                continue
            background_tasks.add_task(
                _send_shortlisted_resume_email,
                candidate['resume_data_id'],
                candidate['candidate_name'],
                candidate['email'],
            )

        print(f"✅ Saved {len(saved_candidates)} candidates")

        # Auto-trigger interview scheduling for shortlisted candidates
        if shortlisted:
            print(f"\n📅 Auto-triggering interview scheduling for {len(shortlisted)} shortlisted candidates...")
            
            # 🔧 FIX: Filter out candidates who already have scheduled interviews
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT LOWER(TRIM(candidate_email))
                    FROM interview_schedules
                    WHERE status = 'scheduled' AND candidate_email IS NOT NULL
                    """
                )
                already_scheduled_emails = {
                    (row[0] or '').strip().lower()
                    for row in cur.fetchall()
                    if row and row[0]
                }
            
            # Filter shortlisted candidates to exclude those already scheduled
            candidates_to_schedule = [
                c for c in shortlisted
                if (c.get('email') or '').strip().lower() not in already_scheduled_emails
            ]
            
            if not candidates_to_schedule:
                print(f"⚠️ All {len(shortlisted)} shortlisted candidates already have interviews scheduled. Skipping.")
            else:
                print(f"✓ {len(candidates_to_schedule)} out of {len(shortlisted)} candidates need scheduling (filtering {len(already_scheduled_emails)} duplicates)")
                
                try:
                    import requests
                    N8N_SCHEDULE_URL = (
                        os.environ.get("N8N_SCHEDULE_WEBHOOK")
                        or os.environ.get("N8N_SCHEDULE_WEBHOOK_URL")
                        or "http://localhost:5678/webhook/schedule-interviews"
                    )
                    schedule_candidates = _candidate_webhook_urls(N8N_SCHEDULE_URL)
                    response = None
                    schedule_errors = []

                    for schedule_url in schedule_candidates:
                        try:
                            response = requests.post(
                                schedule_url,
                                json={
                                    'job_id': jobId,
                                    'shortlisted_candidates': candidates_to_schedule
                                },
                                timeout=30.0,
                            )
                            print(f"Tried schedule webhook: {schedule_url} -> {response.status_code}")
                            if response.status_code < 400:
                                break
                            schedule_errors.append(f"{schedule_url} -> HTTP {response.status_code}")
                        except Exception as req_exc:
                            schedule_errors.append(f"{schedule_url} -> {str(req_exc)}")

                    if response is None or response.status_code >= 400:
                        print(f"⚠️ Interview scheduling trigger failed after retries: {schedule_errors}")
                    else:
                        print(f"✅ Interview scheduling triggered: {response.status_code}")
                        log_phase_completion(
                            "Interview Scheduling",
                            f"source=batch_screen job_id={jobId} candidates={len(candidates_to_schedule)}",
                        )
                except Exception as e:
                    print(f"⚠️ Interview scheduling trigger failed (non-critical): {e}")

        log_phase_completion(
            "Resume Screening",
            f"job_id={jobId} processed={len(saved_candidates)} shortlisted={len(shortlisted)}",
        )
        
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
        conn.rollback()
        print(f"❌ Error in batch screening: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Batch screening error: {str(e)}")
    finally:
        conn.close()

@router.get("/results/{job_id}")
def get_screening_results(job_id: str):
    """
    Fetch screening results for a given job_id directly from the database.
    Used by the frontend to poll for results after uploading resumes via n8n,
    without re-triggering the n8n screening webhook each time.
    """
    conn = get_db_connection()
    try:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, job_id, candidate_name, email, phone,
                    skills, ai_score, interview_status,
                    resume_url, created_at
                FROM resume_data
                WHERE job_id = %s
                ORDER BY ai_score DESC NULLS LAST, created_at DESC;
            """, (job_id,))
            rows = cur.fetchall()

        results = []
        THRESHOLD = 35.0  # Shortlisting threshold in percentage
        for r in rows:
            score = float(r["ai_score"] or 0)
            is_shortlisted = score >= THRESHOLD
            results.append({
                "candidate_name": r["candidate_name"] or "",
                "email": r["email"] or "",
                "phone": r["phone"] or "",
                "skills": r["skills"] or "",
                "match_score": score,
                "file_name": r["resume_url"] or "",   # resume_url used as display name
                "status": "SHORTLISTED" if is_shortlisted else "DECLINED",
                "ai_summary": "",                      # column may not exist in older DBs
            })

        return {"job_id": job_id, "count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()



@router.get("/list")
def list_jobs():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM job_descriptions ORDER BY job_id DESC;")
            jobs = cur.fetchall()
            return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/candidates")
def list_candidates():
    """Get all candidates from the candidates table with their workflow status."""
    conn = get_db_connection()
    try:
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
        conn.close()

@router.get("/database-status")
def get_database_status():
    """Get comprehensive database status across all tables."""
    conn = get_db_connection()
    try:
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
        conn.close()


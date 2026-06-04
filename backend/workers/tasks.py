import base64
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.workers.celery_app import celery_app
from backend.services.resume_service import parse_resume, save_resumes_batch
from backend.phase_logger import log_phase_completion
from backend.api.email_router import send_email_via_smtp

@celery_app.task(name="backend.workers.tasks.process_batch_files_task")
def process_batch_files_task(files_data_b64: list, user_id: int, job_id: str = None):
    """
    Celery task to parse resumes and save them to the database in batch.
    files_data_b64 should be a list of dicts: {"filename": str, "content_b64": str}
    """
    print(f"--> [Celery Worker] Starting processing of batch of {len(files_data_b64)} files")
    parsed_data = []
    for f in files_data_b64:
        try:
            content = base64.b64decode(f["content_b64"])
            data = parse_resume(content, f["filename"])
            parsed_data.append(data)
        except Exception as e:
            print(f"--> [Celery Worker] Error parsing {f['filename']}: {e}")

    if parsed_data:
        try:
            save_resumes_batch(parsed_data, user_id, job_id)
            print(f"--> [Celery Worker] Saved batch of {len(parsed_data)} files to DB")
            log_phase_completion(
                "Resume Screening",
                f"batch_processed={len(parsed_data)} user_id={user_id} job_id={job_id or 'DIRECT'} (Celery)",
            )
            if job_id:
                try:
                    from backend.database import get_redis_client
                    import json
                    redis_client = get_redis_client()
                    if redis_client:
                        channel = f"screening:{job_id}"
                        update_msg = {
                            "type": "screening_update",
                            "status": "completed",
                            "job_id": job_id,
                            "processed_count": len(parsed_data)
                        }
                        redis_client.publish(channel, json.dumps(update_msg))
                        print(f"--> [Celery Worker] Published screening update to Redis channel {channel}")
                except Exception as pub_err:
                    print(f"--> [Celery Worker] Redis publish failed: {pub_err}")
            return {"status": "success", "processed_count": len(parsed_data)}
        except Exception as db_err:
            print(f"--> [Celery Worker] Database save failed: {db_err}")
            raise db_err
    return {"status": "skipped", "processed_count": 0}

@celery_app.task(name="backend.workers.tasks.send_email_task")
def send_email_task(recipient_email: str, recipient_name: str, subject: str, body: str, is_html: bool = False):
    """
    Celery task to send email asynchronously.
    """
    print(f"--> [Celery Worker] Sending email to {recipient_email} - Subject: {subject}")
    try:
        success, message = send_email_via_smtp(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body=body,
            is_html=is_html
        )
        print(f"--> [Celery Worker] Email send result: {success} - {message}")
        return {"success": success, "message": message}
    except Exception as e:
        print(f"--> [Celery Worker] Email send exception: {e}")
        raise e
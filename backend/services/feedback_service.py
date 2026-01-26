from typing import Dict
import json
from backend.database import get_db_connection
from backend.services.scheduling_service import SchedulingService # For email reuse potentially

class FeedbackService:
    def submit_feedback(self, interview_id: int, feedback_data: Dict):
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO interview_feedback 
                    (interview_id, technical_skills, communication_skills, 
                     overall_rating, recommendation, detailed_feedback)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    interview_id,
                    feedback_data.get('technical_skills'),
                    feedback_data.get('communication_skills'),
                    feedback_data.get('overall_rating'),
                    feedback_data.get('recommendation'),
                    feedback_data.get('detailed_feedback')
                ))
                
                # Update status
                cur.execute("UPDATE interview_schedules SET status='completed', feedback_submitted=TRUE WHERE id=%s", (interview_id,))
                conn.commit()
                return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

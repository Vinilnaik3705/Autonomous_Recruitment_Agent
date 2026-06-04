from typing import Dict
from backend.database import get_db_connection
from datetime import datetime

class OnboardingService:
    def generate_offer_letter(self, candidate_name: str, role: str, start_date: str, salary: str):

        return f"""
        Offer Letter

        Dear {candidate_name},

        We are pleased to extend a formal offer for the position of {role} with our team.

        Offer Details:
        - Start Date: {start_date}
        - Salary: {salary}

        Please review the offer and confirm your acceptance within the requested timeline.

        Best regards,
        HR Recruiting Team
        """

    def initiate_onboarding(self, candidate_email: str, offer_details: Dict):
        conn = get_db_connection()
        try:
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                cur.execute("SELECT candidate_name FROM resume_data WHERE email = %s LIMIT 1", (candidate_email,))
                res = cur.fetchone()
                if not res:
                    return False

                name = res['candidate_name']
                letter = self.generate_offer_letter(name, offer_details['role'], offer_details['start_date'], offer_details['salary'])

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS onboarding_tasks (
                        id SERIAL PRIMARY KEY,
                        candidate_email VARCHAR(255),
                        status VARCHAR(50),
                        offer_letter_text TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    INSERT INTO onboarding_tasks (candidate_email, status, offer_letter_text)
                    VALUES (%s, 'offer_sent', %s)
                """, (candidate_email, letter))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
from typing import Dict
from backend.database import get_db_connection
from datetime import datetime

class OnboardingService:
    def generate_offer_letter(self, candidate_name: str, role: str, start_date: str, salary: str):
        # In a real app, this would use a template engine like Jinja2 or python-docx
        return f"""
        OFFER LETTER
        
        Dear {candidate_name},
        
        We are thrilled to offer you the position of {role}!
        
        Start Date: {start_date}
        Salary: {salary}
        
        Welcome to the team!
        """
        
    def initiate_onboarding(self, candidate_email: str, offer_details: Dict):
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Mocking a candidates table lookup or similar
                cur.execute("SELECT candidate_name FROM resume_data WHERE candidate_email = %s LIMIT 1", (candidate_email,))
                res = cur.fetchone()
                if not res:
                    return False
                
                name = res['candidate_name']
                letter = self.generate_offer_letter(name, offer_details['role'], offer_details['start_date'], offer_details['salary'])
                
                # Save to onboarding_tasks
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

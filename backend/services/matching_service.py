from typing import List, Dict
import re
import os
import toml
from backend.database import get_db_connection
import psycopg2.extras
from langchain_openai import OpenAIEmbeddings
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class MatchingService:
    def __init__(self):
        self.embeddings = None
        try:
            # Load API Key logic similar to ResumeAnalyzerAgent
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            secrets_path = os.path.join(project_root, "secrets.toml")
            
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key and os.path.exists(secrets_path):
                secrets = toml.load(secrets_path)
                api_key = secrets.get("OPENAI_API_KEY")
            
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
                self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
                print("OpenAI Embeddings initialized successfully.")
            else:
                print("Warning: OPENAI_API_KEY not found. Matching will fail.")
        except Exception as e:
            print(f"Error initializing OpenAI Embeddings: {e}")
            self.embeddings = None

    def _clean_text(self, text: str) -> str:
        if not text: return ""
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def match_resumes(self, jd_text: str, top_k: int = 5) -> List[Dict]:
        if not self.embeddings:
            print("Embeddings model not loaded (Missing API Key?)")
            return []

        clean_jd = self._clean_text(jd_text)
        
        results = []
        conn = get_db_connection()
        try:
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Fetch all resumes
                cur.execute("""
                    SELECT 
                        rd.id, 
                        rd.candidate_name, 
                        rd.candidate_email,
                        rd.candidate_phone,
                        rd.education,
                        rd.extracted_text, 
                        rd.skills,
                        rf.filename 
                    FROM resume_data rd
                    LEFT JOIN resume_files rf ON rd.resume_file_id = rf.id
                    ORDER BY rd.id ASC
                """)
                resumes = cur.fetchall()
                
                if not resumes:
                    return []

                # Encode JD
                try:
                    jd_vector = self.embeddings.embed_query(clean_jd)
                except Exception as e:
                    print(f"Error embedding JD: {e}")
                    return []

                resume_texts = []
                resume_metadata = []

                for res in resumes:
                    r_text = self._clean_text(res.get('extracted_text', '') or "")
                    
                    raw_skills = res.get('skills', '') or ""
                    if isinstance(raw_skills, list):
                        skills = " ".join(raw_skills)
                    else:
                        skills = raw_skills
                    skills = self._clean_text(skills)

                    # Text + Skills for semantic matching
                    combined_text = f"{r_text} \n Skills: {skills}"
                    
                    resume_texts.append(combined_text)
                    resume_metadata.append(res)
                
                if not resume_texts:
                    return []

                # Encode Resumes (Batch)
                # Note: OpenAI allows batching, but for huge lists we might chunk.
                # Assuming < 2000 resumes for now.
                try:
                    resume_vectors = self.embeddings.embed_documents(resume_texts)
                except Exception as e:
                    print(f"Error embedding resumes: {e}")
                    return []
                
                # Calculate Cosine Similarity
                # jd_vector is 1D, resume_vectors is List[List[float]]
                # Need to convert to numpy for sklearn
                
                jd_vec_np = np.array([jd_vector])
                res_vec_np = np.array(resume_vectors)

                # cosine_similarity expects 2D arrays
                cosine_scores = cosine_similarity(jd_vec_np, res_vec_np)[0]

                for idx, res in enumerate(resume_metadata):
                    score = float(cosine_scores[idx])
                    
                    results.append({
                        "id": res['id'],
                        "Name": res['candidate_name'] or "Unknown Candidate",
                        "Email": res['candidate_email'],
                        "Phone": res['candidate_phone'] or "",
                        "Education": res['education'] or "",
                        "MatchScore": score, 
                        "File": res['filename'] or "Unknown File",
                        "Skills": res['skills'] or "",
                        "ResumeText": res.get('extracted_text', '')
                    })
                
                # Sort by score descending
                results.sort(key=lambda x: x['MatchScore'], reverse=True)
                
                return self._deduplicate(results, top_k)
                
        finally:
            conn.close()

    def _deduplicate(self, results, top_k):
        seen = set()
        unique_results = []
        for r in results:
            key = r['Email'] if r['Email'] else r['File']
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        return unique_results[:top_k]

    def score_new_resumes_for_job(
        self, 
        job_description: str, 
        resume_data_list: List[Dict],  # List of {name, email, phone, resume_text, skills}
        threshold: float = 45.0
    ) -> List[Dict]:
        """
        Score new resumes against a job description using embeddings.
        
        Args:
            job_description: The job description text
            resume_data_list: List of dicts with resume data
            threshold: Score threshold for shortlisting (0-100 scale)
            
        Returns:
            List of scored candidates with shortlist recommendation
        """
        if not self.embeddings:
            print("Embeddings model not loaded (Missing API Key?)")
            return []
        
        if not resume_data_list:
            return []
        
        try:
            # Clean and prepare JD
            clean_jd = self._clean_text(job_description)
            
            # Embed JD
            print(f"Embedding job description...")
            jd_vector = self.embeddings.embed_query(clean_jd)
            
            # Prepare resume texts
            resume_texts = []
            for resume in resume_data_list:
                r_text = self._clean_text(resume.get('resume_text', '') or "")
                skills = resume.get('skills', [])
                if isinstance(skills, list):
                    skills_str = " ".join(skills)
                else:
                    skills_str = str(skills)
                
                # Combine resume text with skills for better matching
                combined_text = f"{r_text} \n Skills: {skills_str}"
                resume_texts.append(combined_text)
            
            # Embed all resumes in batch
            print(f"Embedding {len(resume_texts)} resumes...")
            resume_vectors = self.embeddings.embed_documents(resume_texts)
            
            # Calculate cosine similarity
            jd_vec_np = np.array([jd_vector])
            res_vec_np = np.array(resume_vectors)
            cosine_scores = cosine_similarity(jd_vec_np, res_vec_np)[0]
            
            # Build results
            results = []
            for idx, resume in enumerate(resume_data_list):
                # Convert cosine similarity (0-1) to percentage (0-100)
                score = float(cosine_scores[idx]) * 100
                
                # Apply threshold
                shortlisted = score >= threshold
                
                results.append({
                    'candidate_name': resume.get('name', 'Unknown'),
                    'email': resume.get('email', ''),
                    'phone': resume.get('phone', ''),
                    'skills': resume.get('skills', []),
                    'score': round(score, 2),  # Round to 2 decimal places
                    'shortlisted': shortlisted,
                    'threshold': threshold,
                    'resume_text': resume.get('resume_text', '')[:500]  # First 500 chars for summary
                })
            
            # Sort by score descending
            results.sort(key=lambda x: x['score'], reverse=True)
            
            print(f"✅ Scored {len(results)} resumes. Shortlisted: {sum(1 for r in results if r['shortlisted'])}")
            return results
            
        except Exception as e:
            print(f"Error in score_new_resumes_for_job: {e}")
            import traceback
            traceback.print_exc()
            return []

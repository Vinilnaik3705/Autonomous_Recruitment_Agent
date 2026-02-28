from typing import List, Dict
import re
import os
import toml
import threading
from backend.database import get_db_connection
import psycopg2.extras
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Singleton instance for model caching - avoids reloading the 80MB model on every API call
_matching_service_instance = None

def get_matching_service():
    """Get or create singleton MatchingService instance."""
    global _matching_service_instance
    if _matching_service_instance is None:
        _matching_service_instance = MatchingService()
    return _matching_service_instance


class MatchingService:
    def __init__(self):
        self.model = None
        self.model_lock = threading.Lock()  # Thread-safe lock for model access
        self._load_model()

    def _load_model(self):
        """Load (or reload) the SentenceTransformer model."""
        try:
            print("Loading Sentence Transformer model (all-MiniLM-L6-v2)...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Sentence Transformer model loaded successfully.")
        except Exception as e:
            print(f"Error initializing Sentence Transformer: {e}")
            self.model = None

    def _safe_encode(self, texts):
        """Encode texts, auto-reloading model if the httpx client closed."""
        for attempt in range(2):
            try:
                with self.model_lock:
                    return self.model.encode(texts)
            except Exception as e:
                if 'client has been closed' in str(e).lower() or 'cannot send a request' in str(e).lower():
                    print(f"Model httpx client closed (attempt {attempt+1}), reloading model...")
                    self._load_model()
                    if self.model is None:
                        raise RuntimeError("Model reload failed") from e
                else:
                    raise
        raise RuntimeError("Encode failed after model reload")

    def _clean_text(self, text: str) -> str:
        if not text: return ""
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _calculate_keyword_score(self, jd_text: str, resume_text: str) -> float:
        """Keyword recall with partial matching and TF-IDF-like weighting.
        Longer/rarer JD keywords that match get more weight than short common ones."""
        if not jd_text or not resume_text:
            return 0.0

        # Extended stop words for better signal
        stop_words = {
            'and', 'the', 'is', 'in', 'at', 'of', 'or', 'a', 'an', 'to', 'for', 'with',
            'on', 'by', 'as', 'it', 'that', 'this', 'be', 'are', 'was', 'were', 'will',
            'can', 'has', 'have', 'had', 'do', 'does', 'did', 'not', 'but', 'from',
            'they', 'we', 'you', 'your', 'our', 'their', 'its', 'my', 'me', 'him', 'her',
            'us', 'them', 'who', 'which', 'what', 'when', 'where', 'how', 'all', 'each',
            'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
            'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'should', 'now',
            'also', 'able', 'about', 'above', 'after', 'again', 'any', 'because', 'been',
            'before', 'being', 'between', 'could', 'during', 'get', 'here', 'into',
            'may', 'must', 'need', 'new', 'over', 'shall', 'still', 'these',
            'those', 'through', 'under', 'until', 'upon', 'well', 'would', 'using',
            'work', 'working', 'looking', 'including', 'within', 'etc', 'strong',
            'experience', 'years', 'role', 'team', 'company', 'job', 'candidate'
        }

        jd_words = [w for w in re.findall(r'\w+', jd_text.lower()) if w not in stop_words and len(w) > 2]
        resume_words_set = set(re.findall(r'\w+', resume_text.lower()))

        if not jd_words:
            return 0.0

        # Weight each keyword by length (longer = more specific = more valuable)
        total_weight = 0.0
        matched_weight = 0.0
        seen = set()
        for w in jd_words:
            if w in seen:
                continue
            seen.add(w)
            weight = min(len(w) / 5.0, 2.0)  # Words 5+ chars get weight ≥1.0
            total_weight += weight
            if w in resume_words_set:
                matched_weight += weight

        return matched_weight / total_weight if total_weight > 0 else 0.0

    def _calculate_skill_match_score(self, jd_text: str, resume_skills: list) -> float:
        """Score based on overlap between JD-required skills and resume skills.
        Uses exact match + partial/substring matching for related terms."""
        if not jd_text or not resume_skills:
            return 0.0

        try:
            from backend.services.resume_service import extract_skills
        except ImportError:
            return 0.0

        jd_skills = set(s.lower().strip() for s in extract_skills(jd_text))
        resume_skills_set = set(s.lower().strip() for s in resume_skills if s and str(s).strip())

        if not jd_skills:
            # If JD has no recognizable skills, give partial credit for having skills
            return min(len(resume_skills_set) / 5.0, 1.0) if resume_skills_set else 0.0

        # Exact match score
        exact_matched = jd_skills.intersection(resume_skills_set)
        exact_score = len(exact_matched) / len(jd_skills)

        # Partial match: check if any JD skill is a substring of resume skill or vice versa
        unmatched_jd = jd_skills - exact_matched
        partial_score = 0.0
        for jd_skill in unmatched_jd:
            for r_skill in resume_skills_set:
                if jd_skill in r_skill or r_skill in jd_skill:
                    partial_score += 0.5 / len(jd_skills)  # Half credit for partial match
                    break

        return min(exact_score + partial_score, 1.0)

    def match_resumes(self, jd_text: str, top_k: int = 5, job_id: str = None) -> List[Dict]:
        if not self.model:
            print("Model not loaded.")
            return []

        clean_jd = self._clean_text(jd_text)
        
        results = []
        conn = get_db_connection()
        try:
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Fetch resumes - filter by job_id for session isolation
                if job_id:
                    cur.execute("""
                        SELECT id, candidate_name, email, phone, education,
                               resume_text, skills, job_id
                        FROM resume_data
                        WHERE job_id = %s
                        ORDER BY id ASC
                    """, (job_id,))
                else:
                    cur.execute("""
                        SELECT id, candidate_name, email, phone, education,
                               resume_text, skills, job_id
                        FROM resume_data
                        ORDER BY id ASC
                    """)
                resumes = cur.fetchall()
                
                if not resumes:
                    return []

                # Encode JD (with auto-reload on httpx client closed)
                try:
                    jd_vector = self._safe_encode(clean_jd)
                except Exception as e:
                    print(f"Error embedding JD: {e}")
                    return []

                resume_texts = []
                resume_metadata = []

                for res in resumes:
                    raw_skills = res.get('skills', '') or ""
                    if isinstance(raw_skills, list):
                        skills = " ".join(raw_skills)
                    else:
                        skills = raw_skills
                    skills = self._clean_text(skills)

                    # Use candidate name, education, and skills for semantic matching
                    name = self._clean_text(res.get('candidate_name', '') or "")
                    education = self._clean_text(res.get('education', '') or "")
                    combined_text = f"Name: {name}\nEducation: {education}\nSkills: {skills}"
                    
                    resume_texts.append(combined_text)
                    resume_metadata.append(res)
                
                if not resume_texts:
                    return []

                # Encode Resumes (Batch) (with auto-reload on httpx client closed)
                try:
                    resume_vectors = self._safe_encode(resume_texts)
                except Exception as e:
                    print(f"Error embedding resumes: {e}")
                    return []
                
                # Calculate Cosine Similarity
                jd_vec_np = np.array([jd_vector])
                
                # Ensure resume_vectors is a numpy array
                if not isinstance(resume_vectors, np.ndarray):
                    resume_vectors = np.array(resume_vectors)

                cosine_scores = cosine_similarity(jd_vec_np, resume_vectors)[0]

                for idx, res in enumerate(resume_metadata):
                    semantic_score = float(cosine_scores[idx])
                    
                    # Calculate Keyword Recall Score
                    r_text = resume_texts[idx]
                    keyword_score = self._calculate_keyword_score(clean_jd, r_text)
                    
                    # Calculate Skill Match Score
                    raw_skills = res.get('skills', '') or ''
                    if isinstance(raw_skills, str):
                        skill_list = [s.strip() for s in raw_skills.split(',') if s.strip()]
                    else:
                        skill_list = list(raw_skills)
                    skill_score = self._calculate_skill_match_score(clean_jd, skill_list)
                    
                    # Combined Score: 50% Semantic + 30% Skill Match + 20% Keyword Recall
                    final_score = (semantic_score * 0.50) + (skill_score * 0.30) + (keyword_score * 0.20)
                    
                    results.append({
                        "id": res['id'],
                        "Name": res['candidate_name'] or "Unknown Candidate",
                        "Email": res.get('email') or "",
                        "Phone": res.get('phone') or "",
                        "Education": res.get('education') or "",
                        "MatchScore": final_score, 
                        "File": res.get('job_id') or "Unknown",
                        "Skills": res.get('skills') or ""
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
        threshold: float = 35.0
    ) -> List[Dict]:
        """
        Score new resumes against a job description using Sentence Transformers.
        
        Args:
            job_description: The job description text
            resume_data_list: List of dicts with resume data
            threshold: Score threshold for shortlisting (0-100 scale)
            
        Returns:
            List of scored candidates with shortlist recommendation
        """
        if not self.model:
            print("Model not loaded.")
            return []
        
        if not resume_data_list:
            return []
        
        try:
            # Clean and prepare JD
            clean_jd = self._clean_text(job_description)
            
            # Prepare resume texts
            resume_texts = []
            for resume in resume_data_list:
                r_text = self._clean_text(resume.get('resume_text', '') or "")
                skills = resume.get('skills', [])
                if isinstance(skills, list):
                    skills_str = " ".join(skills)
                else:
                    skills_str = str(skills)
                combined_text = f"{r_text} \n Skills: {skills_str}"
                resume_texts.append(combined_text)
            
            # Embed JD and resumes using safe encode (auto-reloads on httpx client closed)
            print(f"Embedding job description...")
            jd_vector = self._safe_encode(clean_jd)
            
            print(f"Embedding {len(resume_texts)} resumes...")
            resume_vectors = self._safe_encode(resume_texts)
            
            # Calculate cosine similarity
            jd_vec_np = np.array([jd_vector])
            
            if not isinstance(resume_vectors, np.ndarray):
                resume_vectors = np.array(resume_vectors)
                
            cosine_scores = cosine_similarity(jd_vec_np, resume_vectors)[0]
            
            # Build results
            results = []
            for idx, resume in enumerate(resume_data_list):
                semantic_score = float(cosine_scores[idx])
                
                # Keyword Recall Score
                keyword_score = self._calculate_keyword_score(clean_jd, resume_texts[idx])
                
                # Skill Match Score
                resume_skills = resume.get('skills', [])
                if isinstance(resume_skills, str):
                    resume_skills = [s.strip() for s in resume_skills.split(',') if s.strip()]
                skill_score = self._calculate_skill_match_score(clean_jd, resume_skills)
                
                # Combined Score (0-1): 50% Semantic + 30% Skill Match + 20% Keyword Recall
                final_score_norm = (semantic_score * 0.50) + (skill_score * 0.30) + (keyword_score * 0.20)
                
                # Convert to percentage (0-100)
                score = final_score_norm * 100
                
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

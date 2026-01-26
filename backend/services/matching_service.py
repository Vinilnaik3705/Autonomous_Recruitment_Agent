from typing import List, Dict
import re
from backend.database import get_db_connection
import psycopg2.extras

class MatchingService:
    def __init__(self):
        # Optional: Load embeddings model here if needed for heavy lifting
        # For simplicity/speed in this demo, using basic keyword/set matching
        pass

    def _normalize_text(self, text: str) -> set:
        if not text: return set()
        text = text.lower()
        tokens = re.findall(r"\w+", text)
        return set(tokens)

    def match_resumes(self, jd_text: str, top_k: int = 5) -> List[Dict]:
        jd_tokens = self._normalize_text(jd_text)
        
        results = []
        conn = get_db_connection()
        try:
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Fetch all resumes
                # Fetch resumes with filename from resume_files
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
                """)
                resumes = cur.fetchall()
                
                for res in resumes:
                    resume_text = res.get('extracted_text', '')
                    resume_tokens = self._normalize_text(resume_text)
                    
                    if not jd_tokens or not resume_tokens:
                        score = 0.0
                    else:
                        # Jaccard Similarity
                        intersection = jd_tokens.intersection(resume_tokens)
                        union = jd_tokens.union(resume_tokens)
                        score = len(intersection) / len(union)
                    
                    results.append({
                        "id": res['id'],
                        "Name": res['candidate_name'] or "Unknown Candidate",
                        "Email": res['candidate_email'],
                        "Phone": res['candidate_phone'] or "",
                        "Education": res['education'] or "",
                        "MatchScore": score, # 0.0 to 1.0 for frontend multiplication
                        "File": res['filename'] or "Unknown File",
                        "Skills": res['skills'] or ""
                    })
                
                # Sort by score descending
                results.sort(key=lambda x: x['MatchScore'], reverse=True)
                
                # Deduplicate by Email (if present) or Filename
                seen = set()
                unique_results = []
                for r in results:
                    # Use email as primary dedupe key, fallback to filename
                    key = r['Email'] if r['Email'] else r['File']
                    if key not in seen:
                        seen.add(key)
                        unique_results.append(r)
                
                return unique_results[:top_k]
                
        finally:
            conn.close()

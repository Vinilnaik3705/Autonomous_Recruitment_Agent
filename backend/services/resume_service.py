import re
import os
from typing import List, Dict, Any, Optional, Tuple
import json
import fitz           
from docx import Document
from backend.database import get_db_connection

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}"
    r"|\+\d{1,3}\s?\(\d{1,4}\)\s?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}"
    r"|\b91[-.\s]?\d{5}[-.\s]?\d{5}\b"
    r"|\b\+91[-.\s]?\d{5}[-.\s]?\d{5}\b"
    r"|\b0\d{5}[-.\s]?\d{5}\b"
    r"|\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"
    r"|\b\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}\b"
    r"|\b\d{10}\b"
    r"|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"
    r"|\b\d{5}[-.\s]\d{5}\b"
    r"|\b(?:6|7|8|9)\d{9}\b"
    r"|\b\d{4}[-.\s]?\d{3}[-.\s]?\d{3}\b)"
)

MAJOR_SECTION_HINTS = (
    "education", "experience", "work experience", "employment", "skills", "projects",
    "certification", "certifications", "awards", "publications", "summary", "objective",
    "profile", "interests", "languages"
)

HEADER_STOP_WORDS = {
    "degree", "certificate", "degree/certificate", "year", "institute", "cgpa", "gpa",
    "highlights", "responsibilities", "role", "company", "organization", "university",
    "college", "board", "class", "standard", "state", "country", "city", "address",
    "contact", "linkedin", "github", "email", "phone", "mobile", "website", "portfolio"
}

SKILLS_DB = {
    "python", "java", "c++", "c#", ".net", "javascript", "typescript", "react", "angular", "vue", "node.js", "express",
    "django", "flask", "fastapi", "html", "css", "sql", "mysql", "postgresql", "mongodb", "redis", "aws", "azure", "gcp",
    "docker", "kubernetes", "jenkins", "git", "linux", "machine learning", "deep learning", "nlp", "tensorflow", "pytorch",
    "pandas", "numpy", "scikit-learn", "spark", "hadoop", "tableau", "power bi", "excel", "agile", "scrum", "jira",
    "rest api", "graphql", "devops", "ci/cd", "selenium", "cypress", "junit", "mocha", "jest", "php", "ruby", "rails",
    "go", "golang", "rust", "swift", "kotlin", "android", "ios", "flutter", "react native", "unity", "unreal",
    "blockchain", "solidity", "web3", "cybersecurity", "network security", "cloud computing", "big data", "data analysis",
    "project management", "communication", "leadership", "teamwork", "problem solving", "time management", "critical thinking"
}

def clean_line_for_name(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def looks_like_section_header(line: str) -> bool:
    low = line.lower()
    if any(k in low for k in HEADER_STOP_WORDS):
        return True
    if len(line.split()) <= 4 and not re.search(r"\d|@|http", line):
        if any(h in low for h in MAJOR_SECTION_HINTS):
            return True
    return False

def guess_name_from_email(email: str) -> Optional[str]:
    local = email.split("@")[0]
    local = re.sub(r"\d+", "", local)
    parts = [p for p in re.split(r"[._-]+", local) if len(p) > 0]
    parts = [p.capitalize() for p in parts[:4]]
    return " ".join(parts).strip() or None

def extract_name(text: str) -> Optional[str]:
    lines = [clean_line_for_name(l) for l in text.splitlines() if l.strip()]
    if not lines:
        return None

    contact_idx = None
    first_section_idx = None
    for i, l in enumerate(lines[:100]):
        if contact_idx is None and (EMAIL_RE.search(l) or PHONE_RE.search(l)):
            contact_idx = i
        low = l.lower()
        if first_section_idx is None and any(h in low for h in MAJOR_SECTION_HINTS):
            first_section_idx = i
        if contact_idx is not None and first_section_idx is not None:
            break

    stop = min([x for x in [contact_idx, first_section_idx, 30] if x is not None] or [30])
    stop = max(1, min(stop, len(lines)))

    candidates = []
    for idx, line in enumerate(lines[:stop]):
        if looks_like_section_header(line): continue
        if "@" in line or "http" in line or "www." in line: continue
        if re.search(r"\d", line): continue

        tokens = re.findall(r"[A-Za-z][A-Za-z'’\-]*\.?", line)
        if not (1 <= len(tokens) <= 5): continue

        initials = [t for t in tokens if len(re.sub(r"[.'’\-]", "", t)) == 1]
        if len(initials) > 1 or (len(initials) == 1 and tokens.index(initials[0]) != 0): continue

        cap_tokens = sum(1 for t in tokens if t[0].isupper() or t.isupper())
        score = cap_tokens + (2 if len(tokens) in (2, 3) else 0) + (1 if idx <= 5 else 0)
        if line.isupper(): score += 1

        candidates.append((score, idx, " ".join(t.strip(" .") for t in tokens)))

    if candidates:
        candidates.sort(key=lambda x: (-x[0], x[1]))
        return candidates[0][2]

    if contact_idx and contact_idx > 0:
        for j in range(max(0, contact_idx - 3), contact_idx):
            l = lines[j]
            if not (looks_like_section_header(l) or "@" in l or re.search(r"\d", l)):
                tokens = re.findall(r"[A-Za-z][A-Za-z'’\-]*\.?", l)
                if 1 <= len(tokens) <= 5:
                    return " ".join(t.strip(" .") for t in tokens)

    m = EMAIL_RE.search("\n".join(lines[:100]))
    if m:
        return guess_name_from_email(m.group(0))

    return None

def extract_contact_number(text: str) -> Optional[str]:
    all_matches = []
    for match in re.findall(PHONE_RE, text):
        if isinstance(match, tuple): match = max(match, key=len)
        cleaned = re.sub(r"[^\d\+]", "", match)
        if 8 <= len(cleaned.replace("+", "")) <= 15 and match not in all_matches:
            all_matches.append(match)

    if not all_matches: return None

    def phone_score(phone: str) -> int:
        score = 0
        if "+" in phone: score += 2
        if len(re.sub(r"\D", "", phone)) == 10: score += 1
        if re.search(r"[6-9]\d{9}", phone): score += 1
        return score

    all_matches.sort(key=phone_score, reverse=True)
    return all_matches[0]

def extract_email(text: str) -> Optional[str]:

    lines = text.splitlines()
    for line in lines[:50]:                                 
        if re.search(r"(email|e-mail|mail)\s*[:|-]", line, re.IGNORECASE):

            matches = EMAIL_RE.findall(line)
            if matches:
                 return matches[0]

    matches = EMAIL_RE.findall(text)
    if matches:
        for email in matches:
            if not any(stop in email.lower() for stop in ["example.com", "test.com", "placeholder"]):
                return email
    return None

def extract_skills(text: str) -> List[str]:
    found_skills = set()
    text_lower = text.lower()

    for skill in SKILLS_DB:
        if skill in text_lower:

            if len(skill) <= 3:
                if re.search(r"\b" + re.escape(skill) + r"\b", text_lower):
                    found_skills.add(skill)
            else:
                found_skills.add(skill)

    return list(found_skills)

def extract_education(text: str) -> List[str]:

    degree_patterns = [
        r"(?i)\bB\.?\s*Tech\b", r"(?i)\bM\.?\s*Tech\b", 
        r"(?i)\bB\.?\s*E\b", r"(?i)\bM\.?\s*E\b",
        r"(?i)\bB\.?\s*Sc\b", r"(?i)\bM\.?\s*Sc\b",
        r"(?i)\bB\.?\s*C\.?\s*A\b", r"(?i)\bM\.?\s*C\.?\s*A\b",
        r"(?i)\bPh\.?D\b", 
        r"(?i)\bB\.?\s*Com\b", r"(?i)\bM\.?\s*Com\b",
        r"(?i)\bBachelor\b", r"(?i)\bMaster\b"
    ]

    college_keywords = ["University", "Institute", "College", "School", "Academy", "IIT", "NIT", "BITS", "IIIT", "Vellore", "Manipal", "Pilani"]

    noise_keywords = ["project", "experience", "work", "developed", "using", "intern", "internship", "skill", "certificate", "certifications"]

    entries = []
    lines = text.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        line = re.sub(r"(https?://)?(www\.)?(github\.com|linkedin\.com)\S+", "", line, flags=re.IGNORECASE)
        line = re.sub(r"\S+@\S+", "", line)
        line = re.sub(r"[\(\[\{]?\+?\d[\d\-\s]{8,}\d[\)\]\}]?", "", line)                            

        if any(bad in line.lower() for bad in noise_keywords):
            i += 1
            continue

        found_degree = None
        cleaned_line = re.sub(r"\s+", " ", line).strip()

        for pat in degree_patterns:
            m = re.search(pat, cleaned_line)
            if m:
                found_degree = m.group(0)
                break

        if found_degree:

            parts = re.split(r"[|•·]", cleaned_line)
            degree_text = ""
            for part in parts:
                if re.search(re.escape(found_degree), part):
                    degree_text = part.strip()
                    break

            if not degree_text: 
                degree_text = cleaned_line

            if len(degree_text) < 4:                                                              

                if not any(ck.lower() in degree_text.lower() for ck in college_keywords):
                     i += 1
                     continue

            college = None
            cgpa = None

            start_idx = max(0, i - 2)
            end_idx = min(len(lines), i + 4)                           
            context_lines = lines[start_idx:end_idx]

            for ctx_line in context_lines:
                c_line = ctx_line.strip()

                if any(bad in c_line.lower() for bad in noise_keywords): continue

                if not college and any(ck in c_line for ck in college_keywords):

                    if 10 < len(c_line) < 100:
                        college = c_line

                if not cgpa:

                    cgpa_match = re.search(r"\b(?:CGPA|SGPA|GPA)\s*[:=-]?\s*(\d+(?:\.\d+)?)", c_line, re.IGNORECASE)
                    if cgpa_match:
                        cgpa = f"CGPA: {cgpa_match.group(1)}"
                    else:
                        perc_match = re.search(r"(\d+(?:\.\d+)?)\s*%", c_line)
                        if perc_match:
                             val = float(perc_match.group(1))
                             if 40 <= val <= 100:
                                 cgpa = f"{val}%"

            entry_parts = [degree_text]

            if college:

                simp_col = re.sub(r"[^\w]", "", college.lower())
                simp_deg = re.sub(r"[^\w]", "", degree_text.lower())

                if simp_col not in simp_deg:

                     entry_parts.append(college)

            if cgpa:
                entry_parts.append(cgpa)

            full_entry = ", ".join(entry_parts)

            is_dup = False
            for e in entries:
                if degree_text in e: 
                    is_dup = True
                    break

            if not is_dup:
                entries.append(full_entry)

        i += 1

    return entries[:3]

def extract_text_and_links_from_pdf_stream(file_stream: bytes) -> Tuple[str, List[str]]:
    try:
        doc = fitz.open(stream=file_stream, filetype="pdf")
        text = ""
        links = []
        for page in doc:
            text += page.get_text() + "\n"

            page_links = page.get_links()
            for link in page_links:
                if "uri" in link:
                    links.append(link["uri"])
        doc.close()
        return text, links
    except Exception as e:
        raise ValueError(f"PDF read failed: {e}")

def extract_text_from_doc(file_content: bytes) -> str:
    import io
    text_runs = []
    
    # Try UTF-16LE extraction (very common for .doc files)
    try:
        raw_unicode = file_content.decode("utf-16-le", errors="ignore")
        matches = re.findall(r"[\x20-\x7E\s\n\r\t]{4,}", raw_unicode)
        if matches:
            text_runs.extend(matches)
    except Exception:
        pass
        
    # Try ASCII extraction
    try:
        raw_ascii = file_content.decode("ascii", errors="ignore")
        matches = re.findall(r"[\x20-\x7E\s\n\r\t]{4,}", raw_ascii)
        if matches:
            text_runs.extend(matches)
    except Exception:
        pass

    text = "\n".join(text_runs)
    lines = []
    for line in text.splitlines():
        line_clean = re.sub(r"[^\x20-\x7E\s]", "", line).strip()
        if len(line_clean) > 3 and not any(mark in line_clean.lower() for mark in ["normal.dotm", "microsoft word", "title", "subject", "creator"]):
            lines.append(line_clean)
            
    return "\n".join(lines)

def parse_resume(file_content: bytes, filename: str) -> Dict[str, Any]:
    ext = os.path.splitext(filename)[1].lower()
    text = ""
    links = []

    if ext == ".pdf":
        text, links = extract_text_and_links_from_pdf_stream(file_content)
    elif ext == ".docx":
        import io
        doc = Document(io.BytesIO(file_content))
        text = "\n".join([p.text for p in doc.paragraphs])
    elif ext == ".doc":
        text = extract_text_from_doc(file_content)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    name = extract_name(text) or ""
    email = extract_email(text)

    if not email and links:
        for link in links:
            if link.startswith("mailto:"):
                potential_email = link.replace("mailto:", "").strip()
                if EMAIL_RE.match(potential_email):
                    email = potential_email
                    break

    phone = extract_contact_number(text) or ""
    skills = extract_skills(text)
    education = extract_education(text)

    return {
        "filename": filename,
        "name": name,
        "email": email or "",
        "mobile": phone,
        "raw_text": text,
        "skills": ", ".join(skills),
        "education": "; ".join(education)
    }

def save_resume_to_db(data: Dict, user_id: int, job_id: str = None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:

            cur.execute("""
                INSERT INTO resume_data (job_id, candidate_name, email, phone, 
                                         skills, education, interview_status)
                VALUES (%s, %s, %s, %s, %s, %s, 'NEW')
                RETURNING id
            """, (job_id or 'DIRECT', data['name'], data['email'], data['mobile'], 
                  data['skills'], data.get('education', '')))

            row = cur.fetchone()
            file_id = row[0]

        conn.commit()
        return file_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def save_resumes_batch(data_list: List[Dict], user_id: int, job_id: str = None) -> List[int]:
    conn = get_db_connection()
    file_ids = []
    try:
        with conn.cursor() as cur:
            for d in data_list:
                 cur.execute("""
                    INSERT INTO resume_data (job_id, candidate_name, email, phone,
                                             skills, education, interview_status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'NEW')
                    RETURNING id
                """, (job_id or 'DIRECT', d['name'], d['email'], d['mobile'],
                      d.get('skills', ''), d.get('education', '')))

                 row = cur.fetchone()
                 file_id = row[0]
                 file_ids.append(file_id)

        conn.commit()
        return file_ids
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
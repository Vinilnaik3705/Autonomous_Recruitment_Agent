# Error 07: Resume Match Scores Too Low (0.001 – 0.3) — Inaccurate Scoring

## Symptom
All resume scores are extremely low (e.g., `0.001`, `0.05`, `0.12`) even for resumes that clearly match the job description. No candidates are shortlisted because none cross the threshold.

## Root Cause — Jaccard Similarity on Raw Tokens
The original `matching_service.py` used **Jaccard Similarity**, which compares sets of exact words:

```
Jaccard = |intersection(A, B)| / |union(A, B)|
```

This is a poor metric for resumes because:
- It ignores **word importance** (common words like "the", "and" score the same as "Python")
- It ignores **synonyms** ("software engineer" ≠ "developer" even if they mean the same thing)
- A resume with 500 words vs a JD with 200 words will have very low overlap by token count alone

## Solutions Applied (2 Iterations)

### Iteration 1 — TF-IDF Cosine Similarity (Intermediate Fix)
Switched to **TF-IDF Cosine Similarity** using `scikit-learn`:

```python
# backend/services/matching_service.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def match_resumes(job_description: str, resumes: list[str]) -> list[float]:
    corpus = [job_description] + resumes
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(corpus)
    scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])
    return scores[0].tolist()
```

**Result:** Scores improved to `0.4 – 0.7` range for relevant resumes.

### Iteration 2 — Sentence Transformer Embeddings (Final Fix)
For even better accuracy, switched to **semantic embeddings** using `SentenceTransformer`:

```python
# backend/services/scoring_service.py
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')

def score_resume(job_description: str, resume_text: str) -> float:
    embeddings = model.encode([job_description, resume_text])
    score = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return round(float(score) * 100, 2)  # Return as 0–100 scale
```

**Result:** Scores are semantically meaningful — a Python developer resume scores high for a Python job even if it uses different vocabulary.

## Shortlisting Threshold
Set the shortlisting threshold at **45/100** (configurable):
```python
SHORTLIST_THRESHOLD = 45  # Score out of 100
candidate["shortlisted"] = candidate["score"] >= SHORTLIST_THRESHOLD
```

## Scoring Method Comparison

| Method | Accuracy | Speed | Notes |
|---|---|---|---|
| Jaccard Similarity | ❌ Very Low | ⚡ Fast | Exact word overlap only |
| TF-IDF Cosine | ✅ Good | ⚡ Fast | Considers word importance |
| Sentence Embeddings | ✅✅ Best | 🐢 Slower | Semantic understanding |

## Key Lesson
> Use **Sentence Transformers** for resume-to-JD matching. Jaccard and simple keyword matching fail because resumes use varied vocabulary. Semantic embeddings understand that "Python developer" and "Software engineer (Python)" are similar.

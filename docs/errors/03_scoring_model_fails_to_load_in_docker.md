# Error 03: Sentence Transformer Model Fails to Load in Docker (Zero Scores)

## Symptom
- All resume scores are **0** or **null**
- The `/resume/score-with-embeddings` endpoint returns errors
- Backend logs show something like:
  ```
  OSError: [Errno 28] No space left on device
  ```
  or
  ```
  ConnectionError: HTTPSConnectionPool: Max retries exceeded
  ```
  or the model simply never initializes (service shows as "unavailable")

## Root Cause
The `SentenceTransformer` model (`all-MiniLM-L6-v2`) needs to be **downloaded from the internet** the first time it is used. Inside a Docker container:

1. **No internet access at runtime** — The container may be restricted from downloading models during startup
2. **Model cache not persisted** — Every container restart re-downloads the model (or fails if offline)
3. **Disk space** — Model files (~90MB) may exceed Docker's allocated space
4. **Slow cold start** — Model download happens on the first request, causing a timeout

## Solution

### Fix 1 — Download the Model at Build Time (Dockerfile)
Add a step in the `Dockerfile` to download the model while building the image:

```dockerfile
# In backend/Dockerfile

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the model during build (not at runtime)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

This ensures the model is baked into the Docker image and available without internet at runtime.

### Fix 2 — Mount a Volume for Model Cache
In `docker-compose.yml`, mount a persistent volume for the Hugging Face model cache:

```yaml
services:
  backend:
    volumes:
      - huggingface_cache:/root/.cache/huggingface
      
volumes:
  huggingface_cache:
```

This prevents re-downloading the model every time the container restarts.

### Fix 3 — CPU-Only PyTorch (Smaller Download)
Use the CPU-only version of PyTorch to reduce image size and avoid GPU dependency errors:

```dockerfile
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install sentence-transformers
```

### Fix 4 — Lazy Loading with Fallback
In the backend, initialize the model once and handle failures gracefully:

```python
# backend/services/scoring_service.py
_model = None

def get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"[ERROR] Model failed to load: {e}")
            return None
    return _model
```

## Verification
After fixing, check the backend logs on startup:
```
[INFO] Loading SentenceTransformer model...
[INFO] Model loaded successfully.
```

And confirm scores are non-zero when hitting `/resume/score-with-embeddings`.

## Key Lesson
> Never rely on a Docker container downloading ML models at runtime. Always **bake models into the image** or **mount a persistent cache volume**.

FROM python:3.11-slim

WORKDIR /app

# Copy requirements from current directory
COPY requirements.txt .

# Install CPU-only PyTorch first to avoid NVIDIA/CUDA packages
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install all other dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence transformer model so it's baked into the image
# This avoids downloading at runtime (which fails in restricted networks) and
# ensures the model is always available even after container restarts.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2'); print('Model pre-downloaded OK')"

# Copy current directory (backend code) to /app/backend
COPY . backend/

# Add /app to PYTHONPATH so "from backend.services..." works
ENV PYTHONPATH=/app

EXPOSE 8000

# Run from the /app directory, targeting the backend module
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim

WORKDIR /app

# Copy requirements from current directory
COPY requirements.txt .

# Install CPU-only PyTorch to avoid downloading NVIDIA/CUDA packages
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

# Copy current directory (backend code) to /app/backend
COPY . backend/

# Add /app to PYTHONPATH so "from backend.services..." works
ENV PYTHONPATH=/app

EXPOSE 8000

# Run from the /app directory, targeting the backend module
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

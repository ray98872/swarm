# Swarm backend — FastAPI on Python 3.11, deployed to Fly.io free tier.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend package into /app/backend so `backend.main` imports cleanly.
COPY . /app/backend

EXPOSE 8080

# Single uvicorn worker is plenty for demo traffic and keeps the 256MB VM happy.
# In-memory sessions require one worker anyway (see write-up: scale section).
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]

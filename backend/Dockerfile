# Swarm backend — FastAPI on Python 3.11.
# Deployed as a free Hugging Face Space (Docker SDK, CPU Basic, no card).
# HF routes traffic to the port declared as `app_port` in README.md (7860).
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

EXPOSE 7860

# Single uvicorn worker is plenty for demo traffic and keeps memory low.
# In-memory sessions require one worker anyway (see write-up: scale section).
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]

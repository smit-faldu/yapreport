# syntax=docker/dockerfile:1
FROM python:3.11-slim

# 1. Set environment variables for Python and FastAPI
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 2. Install system dependencies
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt/lists \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    sox \
    libsox-fmt-all \
    git

# 3. Copy only requirements first (better layer caching)
COPY requirements.txt .

# RUN --mount=type=cache,target=/root/.cache/pip \
#     pip install torch --index-url https://download.pytorch.org/whl/cu121 && \
#     grep -v "^torch" requirements.txt | pip install -r /dev/stdin

# 4. Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# 5. Create a non-root user for security (crucial for cloud deployments)
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# 6. Copy the rest of the application code
COPY --chown=appuser:appuser . .

EXPOSE 8000

# 7. Use the exec form for CMD
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Multi-stage build for Video Generation Project

# -------------------------
# Stage 1: Builder (Heavy ML Dependencies)
# -------------------------
FROM python:3.10-slim AS builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    sox \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -------------------------
# Stage 2: Runtime (Leaner Image)
# -------------------------
FROM python:3.10-slim

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    sox \
    libsndfile1 \
    libgl1 \
    libglib2.0-0 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the source code, assets, and .env
COPY src/ /app/src/
COPY assets/ /app/assets/
COPY .env /app/.env

# Expose the API port
EXPOSE 8000

# Entry point
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

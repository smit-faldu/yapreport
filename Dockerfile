# Use a lightweight Python base image
FROM python:3.10-slim

# Set environment variables to optimize Python & PyTorch behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Force PyTorch to use CUDA memory efficiently on T4
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    # Suppress warnings from HuggingFace
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

# Set the working directory
WORKDIR /app

# Install system dependencies
# - ffmpeg: Required by whisperX and src/video/muxer.py
# - sox & libsox-fmt-all: Required by src/services/tts_service.py for 'tempo 1.2'
# - git & build-essential: Often required to compile specific ML wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    sox \
    libsox-fmt-all \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install PyTorch with CUDA 12.1 explicitly first to ensure GPU compatibility,
# then install the rest of your requirements.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the FastAPI port
EXPOSE 8000



# Run the FastAPI application using uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
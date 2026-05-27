# syntax=docker/dockerfile:1
# 1. Use the official PyTorch base image (Lightning AI is highly compatible with this).
# This image already contains the heavy CUDA binaries at the system level.
FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

# 2. Set the working directory
WORKDIR /app

# 3. Install System Dependencies first (good for Docker layer caching)
# We include ffmpeg for video, and sox for your 1.2x audio speedup script.
# We use BuildKit cache mounts for apt to speed up installations.
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt/lists \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    sox \
    libsox-fmt-all \
    git

# 4. Copy your requirements file
COPY requirements.txt .

# 5. Install Dependencies
# - First, we remove 'torch' from requirements.txt so we don't explicitly reinstall it,
#   since PyTorch and its optimized CUDA dependencies are pre-installed in the base image.
# - We use a BuildKit cache mount for pip to accelerate package installations.
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -c "with open('requirements.txt', 'r+') as f: lines = [l for l in f if l.strip() != 'torch']; f.seek(0); f.write(''.join(lines)); f.truncate()" && \
    pip install -r requirements.txt

# 6. Copy the rest of your application code
COPY . .

# 7. Expose the port your FastAPI server runs on
EXPOSE 8000

# 8. Start the FastAPI server using Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
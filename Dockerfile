# Use a Debian-based Python image for better PyTorch compatibility
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# --- Layer 1: Install Minimal System Dependencies & Clean Up ---
# We install 'curl' which is often needed by Python libraries for downloading models.
# This replaces the incorrect 'RUN apk add...' line.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies first for layer caching efficiency.
COPY requirements.txt .

# --- Layer 2: Install Python Dependencies ---
# Install all dependencies using the CPU index for PyTorch (to avoid compiling and the need for 'build-essential').
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# --- Layer 3: Application Code ---
# Copy the entire application source code
COPY . .

# Set environment variables to prevent threading/performance issues with PyTorch/NumPy
ENV OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false 

# Expose the port (The Docker Compose file correctly maps 8000)
EXPOSE 8000

# The CMD is for standalone use, but is overridden by the 'command' in docker-compose.yml.
# It's good practice to keep it simple.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
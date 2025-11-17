# Use a Debian-based Python image for better PyTorch compatibility
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Ensure standard build tools are present for certain Python packages
# (e.g., packages with C extensions like Pandas, although not strictly needed for uvicorn)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies first.
# This improves layer caching: if only code changes, dependencies aren't re-installed.
COPY requirements.txt .

# Install Python dependencies globally. uvicorn will be installed here.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application source code
# Make sure your main application code (e.g., 'app' directory) is next to the Dockerfile
COPY . .

# Expose the port (Docker default for uvicorn is 8000)
EXPOSE 8000

# Command to run the application using uvicorn.
# Assumes the app object is 'app' in 'app/main.py'.
# The 'uvicorn' executable is now available globally in this image.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# ==================================
# 1. BUILDER STAGE: Install dependencies
# ==================================
FROM python:3.12-slim AS builder

# Set the working directory for all subsequent commands
WORKDIR /app

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy the requirements file FIRST for efficient layer caching
COPY requirements.txt .

# Install dependencies. The --no-cache-dir flag saves space.
RUN pip install --no-cache-dir -r requirements.txt

# ==================================
# 2. RUNTIME STAGE: Final image for deployment
# ==================================
FROM python:3.12-slim AS runtime

# Set the same working directory
WORKDIR /app

# Copy the installed dependencies and the virtual environment from the builder stage
# This keeps the image small by leaving build tools (like compilers) behind.
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/

# Copy the application source code (your FastAPI files)
# Assuming your main application logic is inside an 'app' directory
COPY app/ app/

# The port your FastAPI app will listen on internally
EXPOSE 8000

# Command to run the application using Uvicorn
# The --host 0.0.0.0 is crucial to allow connections from outside the container
# The format below (exec form) ensures graceful shutdown
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
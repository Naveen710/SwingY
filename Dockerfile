# Use Python 12 for better dependency compatibility
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
        && rm -rf /var/lib/apt/lists/*

        # Install dependencies first (cache layer)
        COPY backend/requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        # Copy backend code
        COPY backend/ .

        # Expose port
        EXPOSE 8000

        # Start command
        CMD ["gunicorn", "main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]

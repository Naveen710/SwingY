# ═══════════════════════════════════════════════════════════════
# BACKEND DOCKERFILE — Swing Trading Scanner API
# ═══════════════════════════════════════════════════════════════
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cache layer)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Create cache directory
RUN mkdir -p .cache

# Expose port (Render injects PORT env var)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run with uvicorn — use PORT env var if set (Render), else default 8000
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2

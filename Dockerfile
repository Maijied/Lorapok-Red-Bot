FROM python:3.11-slim

# Security: run as non-root
RUN useradd -m -u 1000 botuser

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default to dry_run=true — must be explicitly disabled in production
ENV DRY_RUN=true
ENV LOG_LEVEL=INFO
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER botuser

# Default command: worker. Override with COMMAND env var for dashboard.
# Worker:    docker run ... (uses CMD below)
# Dashboard: docker run -e COMMAND=dashboard ...
CMD ["sh", "-c", "if [ \"$COMMAND\" = 'dashboard' ]; then uvicorn app.dashboard.api:app --host 0.0.0.0 --port 8000; else python -m app.main; fi"]

EXPOSE 8000

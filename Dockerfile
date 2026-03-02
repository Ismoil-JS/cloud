# =============================================================================
# Stage 1: Builder — install dependencies into a virtualenv
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build-time system dependencies (gcc, libpq-dev for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies (separate COPY for better layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# =============================================================================
# Stage 2: Production — minimal runtime image
# =============================================================================
FROM python:3.11-slim AS production

# Create a non-root user for security (run as appuser, not root)
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/sh --create-home appuser

WORKDIR /app

# Install only runtime system libraries (libpq5 for psycopg2 at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage (avoids re-installing)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Prevent Python from writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy application source with correct ownership
COPY --chown=appuser:appgroup . .

# Create required runtime directories with correct permissions
RUN mkdir -p staticfiles media && \
    chown -R appuser:appgroup staticfiles media

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--config", "gunicorn.conf.py", "config.wsgi:application"]

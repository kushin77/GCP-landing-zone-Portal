# ============================================================================
# FAANG-Grade Production Dockerfile for Landing Zone Portal Backend
# Multi-stage build with security hardening
# ============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies and compile
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS builder

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Production - Minimal runtime image
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS production

# Security: Run as non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser

# Runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    # Application settings
    APP_HOME=/app \
    PORT=8080 \
    # GCP settings
    GOOGLE_CLOUD_PROJECT="" \
    # Security settings
    ENVIRONMENT=production

WORKDIR $APP_HOME

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appgroup . .

# Remove unnecessary files
RUN rm -rf \
    .git \
    .github \
    __pycache__ \
    *.pyc \
    .pytest_cache \
    .mypy_cache \
    tests/ \
    Dockerfile \
    .dockerignore \
    *.md

# Security hardening
RUN chmod -R 550 $APP_HOME && \
    chmod -R 770 $APP_HOME/__pycache__ 2>/dev/null || true

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE $PORT

# Run with gunicorn for production (uvicorn workers)
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4", "--loop", "uvloop", "--http", "httptools", "--proxy-headers", "--forwarded-allow-ips", "*"]

# -----------------------------------------------------------------------------
# Stage 3: Development - Full tooling for local dev
# -----------------------------------------------------------------------------
FROM production AS development

USER root

# Install dev dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install dev Python packages
RUN pip install \
    debugpy \
    watchfiles \
    ipython

USER appuser

# Override CMD for development with hot reload
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

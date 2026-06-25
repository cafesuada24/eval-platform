# Stage 1: Build virtual environment
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy configuration files and source code for workspace
COPY pyproject.toml uv.lock ./
COPY sdk/ sdk/
COPY backend/ backend/
COPY ai-chat/ ai-chat/

# Sync workspace dependencies targeting backend only
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package backend

# Stage 2: Runtime image
FROM python:3.12-slim AS runtime

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create a non-root user
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code and default fixtures
COPY backend/app /app/app
COPY backend/fixtures /app/fixtures

# Set ownership of the app directory to the appuser
RUN chown -R appuser:appgroup /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Use non-root user
USER appuser

# Expose backend port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://127.0.0.1:8000/healthz || exit 1

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

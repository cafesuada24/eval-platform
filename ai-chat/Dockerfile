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

# Sync workspace dependencies targeting ai-chat only
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package ai-chat

# Stage 2: Runtime image
FROM python:3.12-slim AS runtime

# Set working directory
WORKDIR /app

# Create a non-root user
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy ai-chat code
COPY ai-chat/ /app/ai-chat

# Set ownership to the appuser
RUN chown -R appuser:appgroup /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Use non-root user
USER appuser

# Set runtime working directory to ai-chat so it matches the expected local files
WORKDIR /app/ai-chat

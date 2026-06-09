# =============================================================================
# EE Toolbox Backend - Multi-stage Dockerfile
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder - install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt

RUN pip install --prefix=/install --no-cache-dir -r /tmp/requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Runtime - lean production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY backend/ /app/backend/
COPY pipeline/ /app/pipeline/
COPY data/ /app/data/

# Make entrypoint executable
RUN chmod +x /app/backend/scripts/entrypoint.sh

# Set PYTHONPATH so "from app.database..." (backend) and "from pipeline..." resolve
ENV PYTHONPATH=/app/backend:/app

WORKDIR /app

EXPOSE 8099

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8099/health || exit 1

CMD ["/app/backend/scripts/entrypoint.sh"]

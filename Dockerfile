# =============================================================================
# EE Toolbox Backend - Multi-stage Dockerfile (B2: EC2 ASG runtime)
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder - install Python dependencies + fetch Litestream
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --timeout 60 --retries 5 --prefix=/install -r backend/requirements.txt

# Download Litestream
RUN curl -fsSL https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-amd64.tar.gz \
    | tar -xz -C /usr/local/bin litestream \
    && chmod +x /usr/local/bin/litestream

# ---------------------------------------------------------------------------
# Stage 2: Runtime - lean production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy Litestream binary
COPY --from=builder /usr/local/bin/litestream /usr/local/bin/litestream

# Create non-root user
RUN useradd -m -u 1001 appuser

WORKDIR /app

# Copy application code (NOT data/ — retrieval artifacts cold-load from S3 at startup)
COPY backend/ /app/backend/
COPY pipeline/ /app/pipeline/

# Create data directory for runtime artifacts (populated at startup from S3)
RUN mkdir -p /app/backend/data /app/data && chown -R appuser:appuser /app

# Copy Litestream config
COPY litestream.yml /etc/litestream.yml

# Pre-cache Qwen3-Embedding-0.6B at build time so entrypoint.sh skips download
# This adds ~1.2 GB to the image but eliminates a 5-10 minute runtime download
# that was causing boot times to exceed the ASG health check grace period.
RUN HF_HOME=/app/.cache/huggingface python3 -c "\
from sentence_transformers import SentenceTransformer; \
m = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B'); \
print('Model cached at build time')"

# Make entrypoint executable
RUN chmod +x /app/backend/scripts/entrypoint.sh

# Set PYTHONPATH so "from app...." (backend) and "from pipeline..." resolve
ENV PYTHONPATH=/app/backend:/app
ENV HF_HOME=/app/.cache/huggingface

USER appuser

EXPOSE 8099

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8099/health || exit 1

CMD ["/app/backend/scripts/entrypoint.sh"]

#!/usr/bin/env bash
set -euo pipefail

echo "=== EE Toolbox backend starting ==="
date -u

# ── Fetch API keys from Secrets Manager ──────────────────────────────────────
# The EC2 InstanceRole has secretsmanager:GetSecretValue on this secret.
# Fetched via boto3 (no aws CLI in the image).
# NOTE: the secret's friendly NAME is "ee-toolbox-api-keys"; -vQs462 is only
# the ARN suffix and is NOT accepted as a SecretId by Secrets Manager.
SECRET_NAME="${EE_SECRET_NAME:-ee-toolbox-api-keys}"
echo "Fetching API keys from Secrets Manager: $SECRET_NAME"
SECRET_JSON=$(python3 -c "
import boto3
client = boto3.client('secretsmanager', region_name='eu-central-1')
print(client.get_secret_value(SecretId='$SECRET_NAME')['SecretString'])
")
export ANTHROPIC_API_KEY=$(echo "$SECRET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['ANTHROPIC_API_KEY'])")
export OPENAI_API_KEY=$(echo "$SECRET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['OPENAI_API_KEY'])")
unset SECRET_JSON
echo "API keys loaded."

# ── Restore agent_store.db from Litestream (S3) ──────────────────────────────
AGENT_DB_PATH="${AGENT_STORE_PATH:-/app/backend/data/agent_store.db}"
mkdir -p "$(dirname "$AGENT_DB_PATH")"

if [ -n "${LITESTREAM_S3_PATH:-}" ]; then
    echo "Restoring agent_store.db from Litestream: $LITESTREAM_S3_PATH"
    litestream restore -if-replica-exists -o "$AGENT_DB_PATH" "$LITESTREAM_S3_PATH" || {
        echo "No replica found or restore failed — starting with fresh DB"
    }
else
    echo "LITESTREAM_S3_PATH not set — skipping restore (dev mode)"
fi

# ── Load retrieval artifacts from S3 ─────────────────────────────────────────
# artifact_loader.py will download from EE_RETRIEVAL_S3 if set,
# or use local paths if unset. The WAL settle fix runs inside ensure_artifacts().
if [ -n "${EE_RETRIEVAL_S3:-}" ]; then
    echo "Loading retrieval artifacts from $EE_RETRIEVAL_S3 ..."
    python3 -c "
import logging
logging.basicConfig(level=logging.INFO)
from agents.artifact_loader import ensure_artifacts
paths = ensure_artifacts()
print('Artifacts loaded:', {k: str(v) for k, v in paths.items()})
"
    echo "Artifact loading complete."
fi

# ── Start Litestream replication daemon ──────────────────────────────────────
if [ -n "${LITESTREAM_S3_PATH:-}" ]; then
    # Derive bucket name from s3://BUCKET/path so litestream.yml can reference
    # it via ${LITESTREAM_S3_BUCKET} without a hardcoded account ID.
    export LITESTREAM_S3_BUCKET=$(echo "${LITESTREAM_S3_PATH}" | sed 's|s3://||' | cut -d'/' -f1)
    echo "Starting Litestream replication daemon (bucket: $LITESTREAM_S3_BUCKET)..."
    litestream replicate -config /etc/litestream.yml &
    LITESTREAM_PID=$!
    echo "Litestream PID: $LITESTREAM_PID"
fi

# ── Pre-cache Qwen3-Embedding-0.6B (required for semantic hybrid search) ─────
# retrieval_tools.py sets HF_HUB_OFFLINE=1 via setdefault to prevent HEAD
# requests at query time; the model must therefore be cached before uvicorn
# starts. HF_HUB_OFFLINE=0 as a prefix allows the download for this one step.
echo "Pre-caching embedding model (Qwen/Qwen3-Embedding-0.6B)..."
HF_HUB_OFFLINE=0 python3 -c "
from sentence_transformers import SentenceTransformer
m = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')
print('Embedding model cached successfully')
" && echo "Model ready." || echo "WARNING: model pre-cache failed — corpus_search may error on first use"

# ── Run DB migrations ─────────────────────────────────────────────────────────
# Alembic reads DATABASE_URL_SYNC from env (set by UserData / ECS task def).
# This is idempotent — already-applied revisions are skipped.
if [ -n "${DATABASE_URL_SYNC:-}" ]; then
    echo "Running alembic upgrade head ..."
    cd /app/backend
    alembic upgrade head
    echo "Migrations complete."
else
    echo "DATABASE_URL_SYNC not set — skipping alembic (dev/test mode)"
fi

# ── Start FastAPI ─────────────────────────────────────────────────────────────
# PYTHONPATH=/app/backend:/app (set in Dockerfile) makes app.main resolve.
echo "Starting uvicorn on :8099 ..."
cd /app
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8099 \
    --workers 1 \
    --log-level info \
    --proxy-headers \
    --forwarded-allow-ips='*'

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
    echo "Starting Litestream replication daemon..."
    litestream replicate -config /etc/litestream.yml &
    LITESTREAM_PID=$!
    echo "Litestream PID: $LITESTREAM_PID"
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

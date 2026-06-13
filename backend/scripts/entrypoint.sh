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
_DB_URL=$(echo "$SECRET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('DATABASE_URL',''))")
if [ -n "$_DB_URL" ]; then
    export DATABASE_URL="$_DB_URL"
else
    echo "ERROR: DATABASE_URL key missing or empty in ee-toolbox-api-keys — SQLAlchemy will fail to start. Run ops-fix-db-url.yml to populate the secret." >&2
fi
_DB_URL_SYNC=$(echo "$SECRET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('DATABASE_URL_SYNC',''))")
if [ -n "$_DB_URL_SYNC" ]; then
    export DATABASE_URL_SYNC="$_DB_URL_SYNC"
else
    echo "ERROR: DATABASE_URL_SYNC key missing or empty in ee-toolbox-api-keys." >&2
fi
unset SECRET_JSON
echo "API keys loaded."

# ── Restore agent_store.db from Litestream (S3) ──────────────────────────────
# NON-SILENT restore-on-boot (C6 Wave A, decision 4 + Thread 4).
#
# The DURABLE business data (KPI/analytics/survey/token) now lives in Postgres
# RDS, which survives instance replacement — so a failed SQLite restore no
# longer loses that data. This SQLite store carries session/report-draft state.
# We still make restore LOUD and DETECTABLE: if a Litestream replica EXISTS but
# the restore did not produce a DB file, that is a hard, alertable condition.
# We deliberately do NOT exit non-zero (decision 4: keep the process up so the
# ALB stays healthy and the ASG is not wedged); instead we drop a detectable
# marker file that the app/ops can surface.
AGENT_DB_PATH="${AGENT_STORE_PATH:-/app/backend/data/agent_store.db}"
RESTORE_FAILED_MARKER="$(dirname "$AGENT_DB_PATH")/.restore_failed"
mkdir -p "$(dirname "$AGENT_DB_PATH")"
rm -f "$RESTORE_FAILED_MARKER" || true

if [ -n "${LITESTREAM_S3_PATH:-}" ]; then
    echo "Restoring agent_store.db from Litestream: $LITESTREAM_S3_PATH"
    # Detect whether a replica actually exists (distinguishes genuine first boot
    # from a real restore failure).
    REPLICA_EXISTS="no"
    if litestream snapshots "$LITESTREAM_S3_PATH" 2>/dev/null | grep -q .; then
        REPLICA_EXISTS="yes"
    fi
    echo "Litestream replica present: $REPLICA_EXISTS"

    if litestream restore -if-replica-exists -o "$AGENT_DB_PATH" "$LITESTREAM_S3_PATH"; then
        echo "Litestream restore command completed."
    else
        echo "WARNING: litestream restore returned non-zero."
    fi

    if [ -f "$AGENT_DB_PATH" ]; then
        echo "OK: agent_store.db present after restore ($(stat -c%s "$AGENT_DB_PATH" 2>/dev/null || echo '?') bytes)."
    elif [ "$REPLICA_EXISTS" = "yes" ]; then
        # A replica EXISTS but we have no DB file: this is the silent-data-loss
        # condition we are guarding against. Make it LOUD and DETECTABLE.
        echo "============================================================" >&2
        echo "ERROR: LITESTREAM REPLICA EXISTS BUT RESTORE PRODUCED NO DB!" >&2
        echo "  Replica: $LITESTREAM_S3_PATH" >&2
        echo "  Durable business data is SAFE in Postgres RDS, but the" >&2
        echo "  SQLite session store failed to restore. Investigate." >&2
        echo "============================================================" >&2
        echo "litestream-restore-failed $(date -u +%FT%TZ) replica=$LITESTREAM_S3_PATH" > "$RESTORE_FAILED_MARKER"
        # Do NOT exit: keep the process up (ALB stays healthy, ASG not wedged).
    else
        echo "No Litestream replica yet (genuine first boot) — starting with fresh SQLite DB."
    fi
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
# SUPERVISED + OBSERVABLE (C6 Wave B / Step 0).
#
# Previously this was a bare `litestream replicate ... &` whose stderr went
# nowhere: if the daemon failed to start or died after boot, replication
# silently stopped (observed: WAL writes stopped reaching S3 after an instance
# refresh while /health still reported session_store:connected, because that
# field only probes the local SQLite file — not whether replication is live).
#
# We now (a) tee the daemon's output to the bind-mounted log dir so failures
# are inspectable via `docker logs` AND on-instance, (b) verify the daemon is
# actually alive a moment after launch and log loudly + drop a detectable
# marker if it is not, and (c) supervise it in a background restart loop so a
# transient death self-heals instead of permanently stalling replication.
LITESTREAM_LOG="/var/log/ee-toolbox/litestream.log"
REPLICATE_FAILED_MARKER="/app/backend/data/.replicate_failed"
rm -f "$REPLICATE_FAILED_MARKER" || true
if [ -n "${LITESTREAM_S3_PATH:-}" ]; then
    # Derive bucket name from s3://BUCKET/path so litestream.yml can reference
    # it via ${LITESTREAM_S3_BUCKET} without a hardcoded account ID.
    export LITESTREAM_S3_BUCKET=$(echo "${LITESTREAM_S3_PATH}" | sed 's|s3://||' | cut -d'/' -f1)
    echo "Starting Litestream replication daemon (bucket: $LITESTREAM_S3_BUCKET)..."

    # Supervisor: keep the replicate daemon running for the life of the
    # container; restart with backoff on unexpected exit. Output is tee'd to a
    # persistent log so a dead daemon is always diagnosable.
    (
        while true; do
            echo "[$(date -u +%FT%TZ)] starting litestream replicate (bucket=$LITESTREAM_S3_BUCKET)" >> "$LITESTREAM_LOG"
            litestream replicate -config /etc/litestream.yml >> "$LITESTREAM_LOG" 2>&1
            rc=$?
            echo "[$(date -u +%FT%TZ)] litestream replicate exited rc=$rc — restarting in 5s" >> "$LITESTREAM_LOG"
            echo "litestream-replicate-exited $(date -u +%FT%TZ) rc=$rc" > "$REPLICATE_FAILED_MARKER"
            sleep 5
        done
    ) &
    LITESTREAM_SUP_PID=$!
    echo "Litestream supervisor PID: $LITESTREAM_SUP_PID"

    # Verify the daemon actually came up (catches an immediate-failure loop,
    # e.g. bad config / missing perms / unreadable DB) and surface it loudly.
    sleep 3
    if pgrep -f "litestream replicate" >/dev/null 2>&1; then
        echo "OK: litestream replicate process is running."
    else
        echo "============================================================" >&2
        echo "ERROR: litestream replicate did NOT stay up after launch!" >&2
        echo "  Replication to $LITESTREAM_S3_PATH is NOT active." >&2
        echo "  See $LITESTREAM_LOG for the daemon's own error output." >&2
        echo "============================================================" >&2
        echo "litestream-replicate-not-running $(date -u +%FT%TZ)" > "$REPLICATE_FAILED_MARKER"
        echo "--- tail of $LITESTREAM_LOG ---" >&2
        tail -n 20 "$LITESTREAM_LOG" >&2 2>/dev/null || true
        # Do NOT exit: keep the app up (ALB liveness; durable data is in Postgres).
    fi
fi

# ── Pre-cache Qwen3-Embedding-0.6B (required for semantic hybrid search) ─────
# The model is baked into the Docker image at build time (HF_HOME=/app/.cache/huggingface).
# This step runs with HF_HUB_OFFLINE=1 to verify the cache is present without
# making any network requests. Falls back to a live download only if cache is missing
# (e.g., when running an older image without the baked model).
echo "Pre-caching embedding model (Qwen/Qwen3-Embedding-0.6B)..."
if HF_HUB_OFFLINE=1 python3 -c "
from sentence_transformers import SentenceTransformer
m = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')
print('Embedding model found in cache (no download needed)')
" 2>/dev/null; then
    echo "Model ready (from image cache)."
else
    echo "Model not in cache — downloading from HuggingFace (this may take several minutes)..."
    HF_HUB_OFFLINE=0 python3 -c "
from sentence_transformers import SentenceTransformer
m = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')
print('Embedding model downloaded and cached successfully')
" && echo "Model ready." || echo "WARNING: model pre-cache failed — corpus_search may error on first use"
fi

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

#!/bin/bash
# MGMT deployment + verification script
# Steps: wait for rate limit → trigger deploy → monitor → verify CORS → e2e check
set -euo pipefail

REPO="Smith-synapsis-ai/ee-toolbox-app"
LOG_PREFIX="[MGMT-DEPLOY]"

log() { echo "$(date '+%H:%M:%S') $LOG_PREFIX $*"; }

# ============================================================
# Step 1: Wait for GitHub API rate limit to reset
# ============================================================
log "Step 1: Waiting for GitHub API rate limit to reset..."
while true; do
    REMAINING=$(gh api rate_limit --jq '.rate.remaining' 2>/dev/null || echo "0")
    if [ "$REMAINING" -gt 10 ] 2>/dev/null; then
        log "Rate limit OK — $REMAINING requests remaining"
        break
    fi
    RESET_AT=$(gh api rate_limit --jq '.rate.reset' 2>/dev/null || echo "0")
    NOW=$(date +%s)
    WAIT=$((RESET_AT - NOW + 5))
    if [ "$WAIT" -gt 0 ] && [ "$WAIT" -lt 900 ]; then
        log "Rate limited ($REMAINING remaining). Resets in ${WAIT}s. Waiting..."
        sleep "$WAIT"
    else
        log "Rate limited. Checking again in 30s..."
        sleep 30
    fi
done

# ============================================================
# Step 2: Check if the prd run from main push is still going
# ============================================================
log "Step 2: Checking existing prd deployment from main push..."
PRD_RUN_STATUS=$(gh api repos/$REPO/actions/runs/26466829824 --jq '.status' 2>/dev/null || echo "unknown")
log "Existing prd run status: $PRD_RUN_STATUS"
if [ "$PRD_RUN_STATUS" = "in_progress" ] || [ "$PRD_RUN_STATUS" = "queued" ]; then
    log "PRD deployment still running — this is separate from MGMT, continuing..."
fi

# ============================================================
# Step 3: Trigger workflow_dispatch for mgmt
# ============================================================
log "Step 3: Triggering workflow_dispatch for mgmt environment..."
TRIGGER_RESULT=$(gh workflow run deploy.yml --repo "$REPO" --field environment=mgmt --ref main 2>&1)
TRIGGER_EXIT=$?

if [ $TRIGGER_EXIT -ne 0 ]; then
    log "ERROR: Failed to trigger workflow: $TRIGGER_RESULT"

    # Check if it's because the mgmt environment doesn't have secrets
    if echo "$TRIGGER_RESULT" | grep -qi "not found\|422\|invalid"; then
        log "Trying alternative: check if mgmt environment exists..."
        gh api repos/$REPO/environments --jq '.environments[].name' 2>/dev/null || true
    fi

    log "Attempting to trigger again with -f flag..."
    gh workflow run deploy.yml --repo "$REPO" -f environment=mgmt --ref main 2>&1 || {
        log "FATAL: Could not trigger mgmt deployment. Manual intervention needed."
        exit 1
    }
fi
log "Workflow dispatched successfully!"

# Wait a few seconds for the run to register
sleep 10

# ============================================================
# Step 4: Find and monitor the workflow run
# ============================================================
log "Step 4: Finding the mgmt deployment run..."

# Find the most recent workflow_dispatch run
MGMT_RUN_ID=""
for attempt in $(seq 1 12); do
    MGMT_RUN_ID=$(gh api "repos/$REPO/actions/runs?event=workflow_dispatch&per_page=5" \
        --jq '.workflow_runs | map(select(.head_branch == "main" and .status != "completed")) | .[0].id // empty' 2>/dev/null || echo "")

    if [ -n "$MGMT_RUN_ID" ]; then
        log "Found mgmt run: $MGMT_RUN_ID"
        break
    fi
    log "Run not found yet (attempt $attempt/12), waiting 10s..."
    sleep 10
done

if [ -z "$MGMT_RUN_ID" ]; then
    # Maybe it completed very fast or hasn't started yet; try to find completed recent one
    MGMT_RUN_ID=$(gh api "repos/$REPO/actions/runs?event=workflow_dispatch&per_page=3" \
        --jq '.workflow_runs | map(select(.head_branch == "main")) | .[0].id // empty' 2>/dev/null || echo "")

    if [ -z "$MGMT_RUN_ID" ]; then
        log "WARNING: Could not find mgmt run ID. Will skip run monitoring and go straight to verification."
    fi
fi

# Monitor the run until completion
if [ -n "$MGMT_RUN_ID" ]; then
    log "Monitoring run $MGMT_RUN_ID..."
    POLL_COUNT=0
    MAX_POLLS=60  # 60 * 30s = 30 minutes max

    while [ $POLL_COUNT -lt $MAX_POLLS ]; do
        RUN_DATA=$(gh api "repos/$REPO/actions/runs/$MGMT_RUN_ID" \
            --jq '{status: .status, conclusion: .conclusion}' 2>/dev/null || echo '{"status":"unknown"}')

        STATUS=$(echo "$RUN_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))")
        CONCLUSION=$(echo "$RUN_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('conclusion','') or 'running')")

        # Get current step
        CURRENT_STEP=$(gh api "repos/$REPO/actions/runs/$MGMT_RUN_ID/jobs" \
            --jq '.jobs[-1] | (.steps // [] | map(select(.status == "in_progress")) | .[0].name) // "waiting"' 2>/dev/null || echo "unknown")

        log "Status: $STATUS | Conclusion: $CONCLUSION | Step: $CURRENT_STEP"

        if [ "$STATUS" = "completed" ]; then
            if [ "$CONCLUSION" = "success" ]; then
                log "MGMT deployment completed successfully!"
            else
                log "WARNING: MGMT deployment completed with conclusion: $CONCLUSION"
                # Get failure details
                gh api "repos/$REPO/actions/runs/$MGMT_RUN_ID/jobs" \
                    --jq '.jobs[] | select(.conclusion != "success") | "\(.name): \(.conclusion) - \([.steps[] | select(.conclusion == "failure")] | .[0].name // "unknown step")"' 2>/dev/null || true
            fi
            break
        fi

        POLL_COUNT=$((POLL_COUNT + 1))
        sleep 30
    done

    if [ $POLL_COUNT -ge $MAX_POLLS ]; then
        log "WARNING: Monitoring timed out after 30 minutes. Proceeding to verification anyway."
    fi
fi

# ============================================================
# Step 5: Verify CORS on both environments
# ============================================================
log "Step 5: Verifying CORS on both environments..."

echo ""
log "=== DEV CORS Check ==="
DEV_CORS=$(curl -s -I -X OPTIONS \
    -H "Origin: https://main.damllm6qertma.amplifyapp.com" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Content-Type" \
    https://dev-api-ee-toolbox.synapsis-analytics.com/api/metrics 2>&1)
DEV_CORS_ORIGIN=$(echo "$DEV_CORS" | grep -i "access-control-allow-origin" || echo "NOT FOUND")
DEV_CORS_STATUS=$(echo "$DEV_CORS" | head -1)
log "DEV status: $DEV_CORS_STATUS"
log "DEV CORS header: $DEV_CORS_ORIGIN"

echo ""
log "=== MGMT CORS Check ==="
MGMT_CORS=$(curl -s -I -X OPTIONS \
    -H "Origin: https://main.d15pb16eb2gi8i.amplifyapp.com" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Content-Type" \
    https://api-ee-toolbox.synapsis-analytics.com/api/metrics 2>&1)
MGMT_CORS_ORIGIN=$(echo "$MGMT_CORS" | grep -i "access-control-allow-origin" || echo "NOT FOUND")
MGMT_CORS_STATUS=$(echo "$MGMT_CORS" | head -1)
log "MGMT status: $MGMT_CORS_STATUS"
log "MGMT CORS header: $MGMT_CORS_ORIGIN"

# ============================================================
# Step 6: End-to-end checks
# ============================================================
echo ""
log "Step 6: End-to-end health checks..."

log "--- MGMT Metrics ---"
MGMT_METRICS=$(curl -s https://api-ee-toolbox.synapsis-analytics.com/api/metrics 2>&1)
MGMT_TOOLS=$(echo "$MGMT_METRICS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_tools','ERROR'))" 2>/dev/null || echo "PARSE_ERROR")
log "MGMT tools count: $MGMT_TOOLS"

log "--- MGMT Catalog Search ---"
MGMT_SEARCH=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{"keyword": "climate"}' \
    https://api-ee-toolbox.synapsis-analytics.com/api/search/catalog 2>&1)
MGMT_RESULTS=$(echo "$MGMT_SEARCH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('total',0)} results\")" 2>/dev/null || echo "PARSE_ERROR")
log "MGMT catalog search 'climate': $MGMT_RESULTS"

log "--- DEV Metrics ---"
DEV_METRICS=$(curl -s https://dev-api-ee-toolbox.synapsis-analytics.com/api/metrics 2>&1)
DEV_TOOLS=$(echo "$DEV_METRICS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_tools','ERROR'))" 2>/dev/null || echo "PARSE_ERROR")
log "DEV tools count: $DEV_TOOLS"

# ============================================================
# Summary
# ============================================================
echo ""
echo "============================================================"
log "DEPLOYMENT SUMMARY"
echo "============================================================"
echo ""

# Determine pass/fail
DEV_PASS="FAIL"
MGMT_PASS="FAIL"
if echo "$DEV_CORS_ORIGIN" | grep -qi "amplifyapp.com"; then DEV_PASS="PASS"; fi
if echo "$MGMT_CORS_ORIGIN" | grep -qi "amplifyapp.com"; then MGMT_PASS="PASS"; fi

echo "  DEV  CORS: $DEV_PASS  | Tools: $DEV_TOOLS  | Endpoint: dev-api-ee-toolbox.synapsis-analytics.com"
echo "  MGMT CORS: $MGMT_PASS | Tools: $MGMT_TOOLS | Endpoint: api-ee-toolbox.synapsis-analytics.com"
echo ""

if [ "$DEV_PASS" = "PASS" ] && [ "$MGMT_PASS" = "PASS" ]; then
    log "ALL CHECKS PASSED — Both environments have CORS fix deployed and verified."
else
    log "SOME CHECKS FAILED — Review output above for details."
    if [ "$MGMT_PASS" = "FAIL" ]; then
        log "MGMT CORS still failing. Possible causes:"
        log "  - MGMT deployment hasn't completed yet"
        log "  - mgmt GitHub environment missing AWS_DEPLOY_ROLE_ARN secret"
        log "  - ECS service hasn't rolled the new task definition yet"
    fi
fi

echo ""
log "Script complete."

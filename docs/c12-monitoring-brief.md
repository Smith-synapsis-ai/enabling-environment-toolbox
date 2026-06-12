# C12 Monitoring Brief — EE Toolbox Production

## What We Monitor and Thresholds

| # | Signal | AWS Resource | Metric | Threshold | Rationale |
|---|--------|-------------|--------|-----------|-----------|
| 1 | ALB 5xx errors | ALB `ee-toolbox-alb` | `AWS/ApplicationELB HTTPCode_ELB_5XX_Count` | > 10 in 5 min (Sum) | A handful of bots/crawlers will produce occasional 5xx; >10 in 5 min indicates real backend errors |
| 2 | Target unhealthy host | ALB target group | `AWS/ApplicationELB UnHealthyHostCount` | >= 1 for 2 × 1-min periods | Single-instance setup; any unhealthy host = backend failing ALB health checks |
| 3 | EC2 CPU | ASG `ee-toolbox-prd` | `AWS/EC2 CPUUtilization` | > 85% for 2 × 5-min periods | Agent sessions are CPU-intensive; ASG scaling kicks in at 70% — 85% sustained = scale not keeping up |
| 4 | HTTPS health check | Lambda canary → custom metric | `EEToolbox HealthCheckStatus` | < 1 for 2 × 5-min periods | Lambda checks `/health` every 5 min; two failures = 10 min of backend unavailability |
| 5 | Litestream replication | Lambda canary → S3 check → custom metric | `EEToolbox LitestreamHealth` | < 1 for 2 × 5-min periods | Lambda lists S3 objects under `agent_store/`; if last-modified > 15 min ago, Litestream has stopped replicating |

## Why Lambda Canary Instead of Route53 Health Check

Route53 health check alarms must be created in us-east-1 (Route53 only publishes health-check metrics to us-east-1 CloudWatch). This would require cross-region alarm management and a separate SNS topic in us-east-1, adding complexity. A Lambda canary in eu-central-1 covers both the HTTPS health check AND Litestream S3 staleness in a single function, same region, same SNS topic, simpler to maintain and debug.

## Notification Mechanism

SNS topic `ee-toolbox-prd-alarms`. All 5 alarms route to this topic. Optional email subscription via `AlarmEmail` CloudFormation parameter (empty by default; subscribe post-deploy). All alarms also send OK to the topic on recovery.

## Non-Destructive Guarantee

Monitoring stack creates only: SNS topic, Lambda function, IAM role, EventBridge rule, 5 CloudWatch alarms, 1 CloudWatch log group. No changes to: ALB, ASG, LaunchTemplate, TargetGroup, existing CF stacks, EC2 instances.

---

## C12 Final State — 2026-06-12

### Deployment

| Item | Value |
|------|-------|
| CloudFormation stack | `ee-toolbox-prd-monitoring` — UPDATE_COMPLETE |
| Initial deploy run | https://github.com/Smith-synapsis-ai/enabling-environment-toolbox/actions/runs/27393877584 |
| Merge commit (main) | `17ee6c0e1997d8949a7038328e393675186cfd22` |

### Alarms — Final State (all OK)

| Alarm Name | State | Last Updated (UTC+2) |
|------------|-------|----------------------|
| ee-toolbox-prd-alb-5xx | **OK** | 2026-06-12T06:10:12+02:00 |
| ee-toolbox-prd-alb-unhealthy-hosts | **OK** | 2026-06-12T06:37:34+02:00 |
| ee-toolbox-prd-ec2-cpu-high | **OK** | 2026-06-12T06:10:52+02:00 |
| ee-toolbox-prd-health-check-failing | **OK** | 2026-06-12T08:01:12+02:00 |
| ee-toolbox-prd-litestream-stale | **OK** | 2026-06-12T08:01:56+02:00 |

All 5 alarms in OK state as of 2026-06-12T08:02 CEST.

### Fix Commits

| Commit | Description |
|--------|-------------|
| `d48ede3` | fix(c12): remove deploy.yml self-reference, add SNS subscription, add ops-fix-db workflow |
| `54ea8ed` | fix(c12): ops-fix-db v2 — hardcode container name, avoid Go template braces in SSM payload |
| `827bbb6` | fix(ops): base64-encode SQLite repair script to fix SSM shell quoting (v3) |

### Incident and Resolution

**What happened:** The C12 monitoring PR merge commit (`17ee6c0`) triggered an unintended ASG instance refresh because `deploy.yml` was in its own `paths:` filter. The refresh completed (EndTime: 2026-06-12T04:36:32 UTC) but the new instance started with `database: initializing`. Root cause: Litestream restore failed silently — the previous generation's WAL was incomplete, so no SQLite file was placed at `/app/backend/data/agent_store.db`. The Litestream replicate daemon was running but waiting for the file to appear.

**Alarms fired:**
- `ee-toolbox-prd-health-check-failing` — canary `/health` check returned `initializing` instead of `connected`
- `ee-toolbox-prd-litestream-stale` — no new S3 WAL writes after the refresh (Litestream never started replicating without the DB file)

**Three ops-fix-db.yml workflow iterations:**
1. v1 (run 27396011197) — failed: used `docker ps --format '{{.Names}}'` inside a bash HEREDOC; Go template `{{` braces were corrupted by GitHub Actions
2. v2 (run 27397276465) — failed: fixed the Go template issue by hardcoding `container = 'ee-toolbox-backend'`, but introduced a new shell quoting bug: `f'docker exec {container} python3 -c \"{py_cmd}\"'` where `py_cmd` contained `\"` escapes that became literal `"` in Python, causing `db="` to close the outer bash double-quote and produce `syntax error near unexpected token '('` in SSM
3. v3 (run 27397721486) — **success**: base64-encoded the Python repair script to avoid all shell quoting. SSM command became `docker exec ee-toolbox-backend python3 -c 'import base64; exec(base64.b64decode(b"<b64>").decode())'` — the b64 string contains only `[A-Za-z0-9+/=]`, zero quoting issues

**SSM output (run 27397721486, 2026-06-12T06:00:12 UTC):**
```
=== Health BEFORE fix ===
{"status":"ok","database":"initializing"}
=== Creating DB in container ee-toolbox-backend ===
created
verify ok
=== Health AFTER fix ===
{"status":"ok","database":"connected"}
```

**Self-clear confirmation:** Both alarms cleared at the next canary tick (06:01 UTC), confirmed by `aws cloudwatch describe-alarms --alarm-name-prefix ee-toolbox-prd --profile ai-prod --region eu-central-1` returning all 5 in OK state.

### SNS Topic

| Item | Value |
|------|-------|
| Topic ARN | `arn:aws:sns:eu-central-1:207258148366:ee-toolbox-prd-alarms` |
| Subscriber | `smith-code@synapsis-analytics.com` — PendingConfirmation (email confirmation link sent by SNS; requires inbox confirmation) |

### Non-destructive changes to deploy.yml

Added `paths:` filter to `deploy.yml` `on.push` trigger. The app deploy workflow
now only fires when application code changes — monitoring-only file changes
(e.g., `infra/ee-toolbox-monitoring.yaml`) no longer trigger an instance refresh.

**Caveat:** The PR that added this paths filter changed `deploy.yml` itself, which is in the `paths:` list, causing the deploy workflow to trigger once on the merge commit. The instance refresh completed cleanly but left the app in `database:initializing`. This was the incident described above.

---

### Durable Fix — DB Restore on Boot

**Problem**: Litestream restore can fail silently when the latest generation's WAL is incomplete (e.g., after a clean shutdown or partial replication). The container starts, Litestream runs `restore` which finds no complete snapshot, leaves `/app/backend/data/agent_store.db` absent, and the app enters `initializing` state. The `ops-fix-db.yml` workflow provides a manual recovery path.

**Permanent fix (follow-up task recommended):** Mount the SQLite data directory as a host volume so the DB file persists across container restarts: add `--volume /opt/ee-toolbox/data:/app/backend/data` to the `docker run` command in the EC2 UserData. On boot, Litestream would run `restore` into `/opt/ee-toolbox/data/` (host path), and if restore fails, the previous DB file is still there from the prior instance. This eliminates the cold-start `initializing` problem entirely.

Additionally, add a boot health check to UserData: after `docker run`, poll `/health` for up to 120s and fail the instance if `database: initializing` persists, causing the ASG to replace it rather than serving degraded traffic.

**Status:** Follow-up task created. The `ops-fix-db.yml` workflow serves as the interim manual recovery procedure until the host-volume mount is implemented.

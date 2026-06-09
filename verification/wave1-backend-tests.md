# Wave 1 Backend Tests — Verification Report

**Date:** 2026-05-26
**Status:** ALL TESTS PASSED

---

## Migration (002_analytics_enhancements)

| Test | Result |
|------|--------|
| Upgrade from 001_initial to 002_analytics | PASS |
| Downgrade from 002_analytics to 001_initial | PASS |
| Re-upgrade after downgrade | PASS |

### New Tables Created

| Table | Verified |
|-------|----------|
| conversation_turns | PASS — 9 columns, 2 indexes, 1 check constraint |
| rating_events | PASS — 6 columns, 2 indexes, 1 check constraint, FK CASCADE |
| admin_tokens | PASS — 4 columns, PK on token |
| tool_saves | PASS — 4 columns, 2 indexes, unique constraint, FK CASCADE |

### Column Additions

| Table | Column | Verified |
|-------|--------|----------|
| email_captures | session_id TEXT | PASS |
| email_captures | source TEXT DEFAULT 'modal' | PASS |
| user_sessions | user_type TEXT DEFAULT 'unknown' | PASS |
| user_sessions | utm_source TEXT | PASS |
| user_sessions | utm_medium TEXT | PASS |
| user_sessions | utm_campaign TEXT | PASS |
| user_sessions | is_bot BOOLEAN DEFAULT FALSE | PASS |
| tool_views | duration_seconds INTEGER | PASS |
| tool_views | search_log_id UUID FK | PASS |

### New Indexes (10 total)

| Index | Table | Verified |
|-------|-------|----------|
| ix_user_sessions_started | user_sessions | PASS |
| ix_search_logs_created | search_logs | PASS |
| ix_tool_views_created | tool_views | PASS |
| ix_search_logs_query_type | search_logs | PASS |
| ix_conversation_turns_conv_id | conversation_turns | PASS |
| ix_conversation_turns_session | conversation_turns | PASS |
| ix_rating_events_tool | rating_events | PASS |
| ix_rating_events_created | rating_events | PASS |
| ix_tool_saves_session | tool_saves | PASS |
| ix_tool_saves_tool | tool_saves | PASS |

---

## API Endpoint Tests

### Health Check
- `GET /health` → `{"status":"ok","database":"connected"}` — PASS

### Admin Login (DB-persisted tokens)
- `POST /api/admin/login` with correct creds → 200 + token — PASS
- `POST /api/admin/login` with wrong creds → 401 — PASS
- Token stored in admin_tokens table with 24h expiry — PASS
- Token verified via DB lookup in `verify_admin_token()` — PASS
- `GET /api/admin/tools` with valid token → 200 (92 tools) — PASS

### Email Capture
- `POST /api/email-capture` with valid email → 200 + captured — PASS
- CGIAR email classified as user_type="internal" — PASS
- External email classified as user_type="external" — PASS
- Invalid email format → 422 — PASS
- Idempotency: same email twice → upsert, 1 row — PASS
- session_id and source='modal' stored correctly — PASS

### Tool Save/Unsave
- `POST /api/tools/{id}/save` → saved — PASS
- `DELETE /api/tools/{id}/save` → unsaved — PASS
- Idempotency: same save twice → 1 row (ON CONFLICT DO NOTHING) — PASS
- Missing X-Session-ID → 400 — PASS

### Rating with Event Logging
- `POST /api/tools/{id}/rate` → upsert in user_ratings + INSERT in rating_events — PASS
- Re-rating: user_ratings updated, rating_events has BOTH entries (immutable log) — PASS
- Check constraint enforced (rating 1-5) — PASS

### Bot Detection
- Googlebot user-agent → is_bot=TRUE in DB — PASS
- Normal browser user-agent → is_bot=FALSE in DB — PASS
- Bot detection integrated into TrackingService.ensure_session() — PASS

### Session Tracking
- last_active_at updated on subsequent requests — PASS
- Session created on first request with X-Session-ID — PASS

---

## Configuration

| Item | Status |
|------|--------|
| config.py has all 8 new settings | PASS |
| .env has all required variables | PASS |
| OPENAI_API_KEY populated from environment | PASS |
| CORS_ORIGINS configurable via settings | PASS |
| Admin creds from settings (not os.environ) | PASS |

---

## Files Created/Modified

### New Files
- `backend/alembic/versions/002_analytics_enhancements.py`
- `backend/app/models/conversation.py`
- `backend/app/models/rating_event.py`
- `backend/app/models/admin_token.py`
- `backend/app/models/tool_save.py`
- `backend/app/middleware/__init__.py`
- `backend/app/middleware/bot_detection.py`

### Modified Files
- `backend/app/config.py` — added 8 settings
- `backend/app/models/__init__.py` — exports 4 new models
- `backend/app/models/analytics.py` — new columns on EmailCapture, UserSession, ToolView, SearchLog + indexes
- `backend/app/routers/admin.py` — DB-persisted tokens with 24h expiry
- `backend/app/routers/tools.py` — rating_events INSERT, save/unsave endpoints, email-capture endpoint
- `backend/app/routers/chat.py` — passes session_id to generate_response
- `backend/app/services/chat_service.py` — DB persistence of conversation turns
- `backend/app/services/tracking.py` — bot detection in ensure_session
- `backend/app/main.py` — imports all models, uses settings for CORS, session tracking with bot detection
- `.env` — all environment variables populated

---

## Backend Status

Server running on port 8099, all endpoints functional, no errors in logs.

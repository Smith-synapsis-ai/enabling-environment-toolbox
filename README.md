# Enabling Environment Toolbox

CGIAR Enabling Environment Toolbox — AI-guided discovery of tools, frameworks, and methods for agricultural innovation scaling.

## Quick Start

```bash
# 1. Start PostgreSQL (port 5433)
docker compose up -d

# 2. Install Python dependencies
cd backend
pip install -r requirements.txt

# 3. Run database migrations
alembic upgrade head

# 4. Seed initial prompts
python scripts/seed_prompts.py

# 5. Verify schema
python scripts/verify_schema.py

# 6. Start the API server
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check (includes DB connectivity) |
| GET | /api/prompts | List all prompt versions |
| GET | /api/prompts/{name}/active | Get active prompt by name |
| POST | /api/prompts | Create new prompt version |
| PUT | /api/prompts/{id}/activate | Activate a prompt version |

## Configuration

Copy `.env.example` to `.env` and adjust values as needed:

```
DATABASE_URL=postgresql+asyncpg://ee_user:ee_dev_password@localhost:5433/ee_toolbox
DATABASE_URL_SYNC=postgresql://ee_user:ee_dev_password@localhost:5433/ee_toolbox
```

## Database

PostgreSQL 16 with pgvector extension, running in Docker on port 5433.

Tables: tools, user_ratings, search_logs, tool_views, user_sessions, email_captures, prompt_versions, prompt_eval_results.

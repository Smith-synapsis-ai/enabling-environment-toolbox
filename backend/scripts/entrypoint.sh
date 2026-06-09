#!/bin/bash
set -e

echo "=== EE Toolbox Backend Startup ==="

# Run Alembic migrations (idempotent — safe to run on every start)
echo "Running Alembic database migrations..."
cd /app/backend
alembic upgrade head
echo "Migrations complete."

# Start the application
echo "Starting uvicorn..."
cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8099 --workers 2

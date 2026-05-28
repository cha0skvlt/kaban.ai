#!/bin/sh
set -e
cd /app
python -m alembic -c alembic.ini upgrade head
exec uvicorn app:app --host 0.0.0.0 --port 8000

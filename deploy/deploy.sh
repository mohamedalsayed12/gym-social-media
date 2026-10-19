#!/usr/bin/env bash
# Runs on the droplet after the deploy job has checked out origin/main.
# Installs dependencies, migrates the database and restarts the API.
# Settings come from .env, which config.py loads itself.
set -euo pipefail

APP_DIR=/home/fastapi/app
cd "$APP_DIR"

.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/alembic upgrade head

sudo /usr/bin/systemctl restart gunicorn
sleep 2
curl -fsS http://127.0.0.1:8000/openapi.json > /dev/null
echo "Deployed $(git rev-parse --short HEAD)"

#!/usr/bin/env bash
# Runs on the droplet. Pulls main, installs dependencies, migrates the
# database and restarts the API. Called by the GitHub Actions deploy job.
set -euo pipefail

APP_DIR=/home/fastapi/app
cd "$APP_DIR"

git fetch --quiet origin main
git reset --hard origin/main

.venv/bin/pip install --quiet -r requirements.txt
set -a; . ./.env; set +a
.venv/bin/alembic upgrade head

sudo /usr/bin/systemctl restart gunicorn
sleep 2
curl -fsS http://127.0.0.1:8000/openapi.json > /dev/null
echo "Deployed $(git rev-parse --short HEAD)"

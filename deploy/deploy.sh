#!/usr/bin/env bash
# Runs on the droplet as the "fastapi" user. Called by the GitHub Actions deploy job
# after it has checked out origin/main in /home/fastapi/app and copied the built
# frontend to /home/fastapi/app/frontend-dist.new.
#
# Steps: back up the database, install dependencies, run migrations, publish the
# frontend, restart the API and check it answers.
set -euo pipefail

APP_DIR=/home/fastapi/app
WEB_DIR=/var/www/gym-social
BACKUP_DIR=/home/fastapi/backups
cd "$APP_DIR"

echo "==> Backing up the database"
mkdir -p "$BACKUP_DIR"
# Build a libpq URL from the same settings the app uses (.env), so pg_dump hits
# the same database. The driver suffix (+psycopg2) is removed for pg_dump.
DB_URL=$(.venv/bin/python -c "from app.db.database import build_database_url; from app.core.config import settings; print(build_database_url(settings).set(drivername='postgresql').render_as_string(hide_password=False))")
BACKUP_FILE="$BACKUP_DIR/gym-$(date -u +%Y%m%dT%H%M%SZ).dump"
pg_dump --format=custom --file="$BACKUP_FILE" "$DB_URL"
echo "    saved $BACKUP_FILE"
# Keep the 10 most recent backups.
ls -1t "$BACKUP_DIR"/gym-*.dump | tail -n +11 | xargs -r rm --

echo "==> Installing dependencies"
.venv/bin/pip install --quiet -r requirements.txt

echo "==> Running migrations"
.venv/bin/alembic upgrade head

echo "==> Publishing the frontend"
if [ -d "$APP_DIR/frontend-dist.new" ]; then
  mkdir -p "$WEB_DIR"
  rsync -a --delete "$APP_DIR/frontend-dist.new/" "$WEB_DIR/"
  rm -rf "$APP_DIR/frontend-dist.new"
else
  echo "    no new frontend build found, keeping the current one"
fi

echo "==> Restarting the API"
sudo /usr/bin/systemctl restart gunicorn
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://127.0.0.1:8000/health > /dev/null; then
    echo "Deployed $(git rev-parse --short HEAD)"
    exit 0
  fi
  sleep 2
done
echo "The API did not come back after restarting. Check: sudo journalctl -u gunicorn -n 50" >&2
exit 1

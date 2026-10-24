#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${APP_DIR:-/home/fastapi/app}
APP_USER=${APP_USER:-fastapi}
SERVICE=${SERVICE:-gunicorn}

as_app() { sudo -u "$APP_USER" "$@"; }

cd "$APP_DIR"
if [ ! -d .git ]; then
    echo "$APP_DIR is not a git checkout. Clone the repo there first." >&2
    exit 1
fi

echo "==> Pulling main"
as_app git fetch --quiet origin main
as_app git merge --ff-only origin/main
echo "Now at $(as_app git log -1 --format='%h %s')"

echo "==> Checking SECRET_KEY"
key=$(grep -E '^SECRET_KEY=' .env | head -1 | cut -d= -f2- | tr -d "\"'" || true)
if [ "${#key}" -lt 32 ]; then
    backup=".env.backup.$(date +%Y%m%d%H%M%S)"
    cp -p .env "$backup"
    new_key=$(openssl rand -hex 32)
    if grep -qE '^SECRET_KEY=' .env; then
        sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$new_key/" .env
    else
        echo "SECRET_KEY=$new_key" >> .env
    fi
    echo "SECRET_KEY was under 32 characters, so it was replaced (old .env saved as $backup)."
    echo "Everyone will need to sign in again once."
fi

echo "==> Installing dependencies"
as_app .venv/bin/pip install --quiet -r requirements.txt

echo "==> Updating the systemd unit"
unit="/etc/systemd/system/$SERVICE.service"
if ! cmp -s deploy/gunicorn.service "$unit"; then
    [ -f "$unit" ] && cp -p "$unit" "$unit.backup"
    cp deploy/gunicorn.service "$unit"
    systemctl daemon-reload
    echo "Installed new $unit"
fi

echo "==> Updating nginx"
site=$(grep -lE 'server_name .*(api\.music4u\.world|178\.128\.32\.16)' /etc/nginx/sites-enabled/* 2>/dev/null | head -1 || true)
if [ -n "$site" ]; then
    target=$(readlink -f "$site")
    if ! cmp -s deploy/nginx.conf "$target"; then
        cp -p "$target" "$target.backup"
        cp deploy/nginx.conf "$target"
        if nginx -t 2>/dev/null; then
            systemctl reload nginx
            echo "Reloaded nginx with the new config"
        else
            cp -p "$target.backup" "$target"
            echo "New nginx config failed nginx -t, kept the old one" >&2
        fi
    fi
else
    echo "No enabled nginx site for this app found, skipping"
fi

echo "==> Restarting (migrations run before the app starts)"
systemctl restart "$SERVICE"

for _ in $(seq 1 20); do
    if curl -fsS http://127.0.0.1:8000/health >/dev/null; then
        echo "==> Healthy"
        exit 0
    fi
    sleep 2
done

echo "Health check failed. Recent logs:" >&2
journalctl -u "$SERVICE" -n 50 --no-pager >&2
exit 1

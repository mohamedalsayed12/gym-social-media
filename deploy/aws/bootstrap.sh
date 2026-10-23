#!/bin/bash
# EC2 user data. provision.sh fills in the __PLACEHOLDERS__ before launching the instance.
# Installs the app the same way as the VPS (systemd + gunicorn behind nginx), reading the
# database password from Secrets Manager through the instance role.
set -euxo pipefail
exec > >(tee /var/log/gym-social-bootstrap.log) 2>&1

DB_HOST="__DB_HOST__"
SECRET_ARN="__SECRET_ARN__"
BUCKET="__BUCKET__"
REGION="__REGION__"
REPO="__REPO__"
APP=/home/fastapi/app

export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -yq python3-venv git nginx postgresql-client jq certbot python3-certbot-nginx
snap install aws-cli --classic

# A t3.micro has 1 GB of RAM; swap stops pip or a traffic spike from getting the app OOM-killed.
if [ ! -f /swapfile ]; then
    fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

id fastapi >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash fastapi
[ -d "$APP/.git" ] || sudo -u fastapi git clone "https://github.com/$REPO.git" "$APP"
sudo -u fastapi python3 -m venv "$APP/.venv"
sudo -u fastapi "$APP/.venv/bin/pip" install --quiet -r "$APP/requirements.txt"

if [ ! -f "$APP/.env" ]; then
    secret=$(aws secretsmanager get-secret-value --region "$REGION" --secret-id "$SECRET_ARN" \
        --query SecretString --output text)
    db_user=$(jq -r .username <<<"$secret")
    db_pass=$(jq -r .password <<<"$secret" | python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip(), safe=''))")
    umask 077
    cat > "$APP/.env" <<EOF
DATABASE_URL=postgresql://$db_user:$db_pass@$DB_HOST:5432/gymsocial?sslmode=require
SECRET_KEY=$(openssl rand -hex 32)
S3_BUCKET=$BUCKET
S3_REGION=$REGION
EOF
    chown fastapi:fastapi "$APP/.env"
fi

cp "$APP/deploy/gunicorn.service" /etc/systemd/system/gunicorn.service

# HTTP only to start with; certbot adds HTTPS once the domain points here.
cat > /etc/nginx/sites-available/gym-social <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name api.music4u.world _;
    client_max_body_size 6m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;
    }
}
EOF
ln -sf /etc/nginx/sites-available/gym-social /etc/nginx/sites-enabled/gym-social
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

systemctl daemon-reload
systemctl enable --now gunicorn
for _ in $(seq 1 30); do
    curl -fsS http://127.0.0.1:8000/health && break
    sleep 2
done
echo "BOOTSTRAP COMPLETE"

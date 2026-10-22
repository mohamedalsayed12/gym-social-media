# Deploying to DigitalOcean

The app runs on one DigitalOcean droplet:

| URL | What it serves |
| --- | --- |
| `https://api.music4u.world/` | The React app (built files in `/var/www/gym-social`) |
| `https://api.music4u.world/api/...` | The FastAPI API (Nginx removes the `/api` prefix) |
| `https://api.music4u.world/docs` | FastAPI's interactive docs |

The API sits under `/api` because the React app has its own `/workouts/...` pages.

## How a deploy works

Every push to `main` runs `.github/workflows/build-deploy.yml`:

1. Run the backend tests and lint.
2. Build the React app with `VITE_API_URL=/api`.
3. SSH into the droplet, reset `/home/fastapi/app` to `origin/main`, and copy the built frontend.
4. Run `deploy/deploy.sh` on the droplet: back up the database, install dependencies,
   run migrations, publish the frontend, restart the API and check `/health`.
5. Check the live site serves the new API and the React app.

## One-time setup

Do this once, before merging the first deploy to `main`.

### 1. On the droplet

Open the droplet's console in DigitalOcean (Droplets > your droplet > Access >
Launch Droplet Console), log in as a user with sudo, and paste:

```bash
# Tools the deploy script uses
sudo apt-get update && sudo apt-get install -y rsync postgresql-client curl git

# Folder Nginx serves the React app from, owned by the app user
sudo mkdir -p /var/www/gym-social && sudo chown fastapi:fastapi /var/www/gym-social

# Make sure the app folder is a git checkout of this repo
sudo -u fastapi bash -c '
set -e
cd /home/fastapi/app
[ -d .git ] || git init -q
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/mohamedalsayed12/gym-social-media.git
git fetch -q origin main
git reset -q --hard origin/main
'

# A deploy key for GitHub Actions to log in as "fastapi"
sudo -u fastapi bash -c '
set -e
mkdir -p ~/.ssh && chmod 700 ~/.ssh
[ -f ~/.ssh/github_deploy ] || ssh-keygen -t ed25519 -N "" -C github-deploy -f ~/.ssh/github_deploy -q
grep -qxF "$(cat ~/.ssh/github_deploy.pub)" ~/.ssh/authorized_keys 2>/dev/null || cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
'

# Let "fastapi" restart the API without a password (and nothing else)
echo 'fastapi ALL=(root) NOPASSWD: /usr/bin/systemctl restart gunicorn' | sudo tee /etc/sudoers.d/fastapi-deploy >/dev/null
sudo chmod 440 /etc/sudoers.d/fastapi-deploy
sudo visudo -cf /etc/sudoers.d/fastapi-deploy

# The app now starts from app.main:app
sudo cp /home/fastapi/app/gunicorn.service /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload

# Allow the site's own address for CORS
grep -q '^CORS_ORIGINS=' /home/fastapi/app/.env \
  && sudo sed -i 's#^CORS_ORIGINS=.*#CORS_ORIGINS=https://api.music4u.world#' /home/fastapi/app/.env \
  || echo 'CORS_ORIGINS=https://api.music4u.world' | sudo tee -a /home/fastapi/app/.env >/dev/null

# Show the Nginx site files so you know which one to replace in step 2
ls -l /etc/nginx/sites-enabled/

echo "----- COPY EVERYTHING BELOW INTO THE DROPLET_SSH_KEY SECRET -----"
sudo cat /home/fastapi/.ssh/github_deploy
```

Check the output: `visudo` should say **parsed OK**.

### 2. Replace the Nginx config

Replace the site file you saw in step 1 (shown here as `SITE`, for example `default` or
`fastapi`) with this repo's config, then test and reload:

```bash
SITE=default   # change to the file name listed in /etc/nginx/sites-enabled/
sudo cp /etc/nginx/sites-available/$SITE /etc/nginx/sites-available/$SITE.backup
sudo cp /home/fastapi/app/deploy/nginx.conf /etc/nginx/sites-available/$SITE
sudo nginx -t && sudo systemctl reload nginx
```

If `nginx -t` reports an error, nothing is reloaded. Restore the backup with
`sudo cp /etc/nginx/sites-available/$SITE.backup /etc/nginx/sites-available/$SITE`.

### 3. Add the GitHub secrets

In GitHub: Settings > Secrets and variables > Actions > New repository secret.

| Secret | Value |
| --- | --- |
| `DROPLET_HOST` | `178.128.32.16` |
| `DROPLET_USER` | `fastapi` |
| `DROPLET_SSH_KEY` | Everything printed after the "COPY..." line in step 1, including the BEGIN and END lines |

The existing `DATABASE_*`, `SECRET_KEY`, `ALGORITHM` and `ACCESS_TOKEN_EXPIRE_MINUTES`
secrets are still used by the test job.

### 4. Deploy

Merge to `main`. Watch the **deploy** job in the Actions tab.

## Important: the first deploy changes the database

The migration `c4e8a1d92b17` turns the old posts-and-votes schema into the gym schema.
**User accounts are kept, but old posts and votes are deleted.** The deploy script backs
up the database first to `/home/fastapi/backups/gym-<date>.dump`. To restore a backup:

```bash
sudo -u fastapi pg_restore --clean --if-exists --dbname "<database url>" /home/fastapi/backups/gym-<date>.dump
```

## Checking it worked

- `https://api.music4u.world/` shows the app's login page.
- `https://api.music4u.world/api/health` returns `{"status": "ok"}`.
- `https://api.music4u.world/docs` lists the workouts, feed, communities and users endpoints.

If the API does not start, run `sudo journalctl -u gunicorn -n 50` on the droplet.

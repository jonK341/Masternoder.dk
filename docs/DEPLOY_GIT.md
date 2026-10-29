# Git deploy on the live server <!-- pragma: allowlist secret -->

Use **git on the server** at `/var/www/html` instead of SFTP from a laptop. After code is on `main` (e.g. PR #130), deploy with one script.

## One-time setup (if `/var/www/html` is not a git repo yet)

**Option A — clone fresh (simplest on a new box)**

```bash
# Back up existing tree and secrets first
test -f /var/www/html/.env && cp -a /var/www/html/.env /root/html.env.bak

mv /var/www/html /var/www/html.pre-git.$(date +%Y%m%d) 2>/dev/null || true
git clone https://github.com/jonK341/Masternoder.dk.git /var/www/html  <!-- pragma: allowlist secret -->
cp -a /root/html.env.bak /var/www/html/.env   # restore secrets
chown -R www-data:www-data /var/www/html/logs /var/www/html/instance 2>/dev/null || true
```

**Option B — turn the existing tree into a checkout**

```bash
cd /var/www/html
git init
git remote add origin https://github.com/jonK341/Masternoder.dk.git  <!-- pragma: allowlist secret -->
git fetch origin main
git checkout -B main origin/main
# Keep local .env, data/, logs/ — they stay untracked or gitignored
```

Use a **deploy key** or **HTTPS token** if the repo is private (`git config credential.helper store` after one successful pull).

**Option C — bootstrap script (no git repo yet; run once on the server)**

`git pull` will always say *not a git repository* until `.git` exists. From Termux, SSH to the server, then:

```bash
apt update && apt install -y git    # if `git` is missing
curl -fsSL "https://raw.githubusercontent.com/jonK341/Masternoder.dk/main/scripts/bootstrap_git_on_server.sh" | bash  <!-- pragma: allowlist secret -->
```

(If that URL 404s before the script is on `main`, use branch `cursor/container-deploy-faa3` in the path instead of `main`.)

Then `git pull --ff-only origin main` will work.

SSH to the server (or `pct enter` your LXC), then:

```bash
cd /var/www/html
bash scripts/container_deploy.sh
```

The script will:

1. `git pull --ff-only origin main`
2. `pip install -r requirements.txt` (repo root)
3. Prompt for **`MN2_WALLET_PASSPHRASE`** (Enter to skip if already set)
4. Run `scripts/production_apply_routes.sh` (cache clear + restart uwsgi/nginx) <!-- pragma: allowlist secret -->
5. Optionally refresh the Suno Docker sidecar if Docker is installed

## Manual shortcut (same as pull + migrations + apply routes)

```bash
cd /var/www/html
git fetch origin main && git checkout main && git pull --ff-only origin main
python3 scripts/apply_db_migrations.py
bash scripts/production_apply_routes.sh  <!-- pragma: allowlist secret -->
```

`apply_db_migrations.py` runs feature migrations, point-ledger bootstrap, and additive MN2 DDL. Optional full MN2 JSON backfill: `RUN_MN2_BACKFILL=1 python3 scripts/apply_db_migrations.py`. Step **[0/7]** of `production_apply_routes.sh` runs `apply_db_migrations.py` automatically.  <!-- pragma: allowlist secret -->

## Verify

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/api/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/api/version
```

From your browser: hard refresh (Ctrl+F5) on the pages you changed.

## When git is not enough

- **Systemd/cron under `/etc`**: still install via `python scripts/deploy.py mn2_env …` once from a machine with SSH, or copy cron files by hand.
- **Large binary/media**: not in git; use existing camgirls/media deploy manifests if needed.

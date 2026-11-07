#!/usr/bin/env bash
# Git-based deploy on the live server (run inside /var/www/html). <!-- pragma: allowlist secret -->
#
#   ssh root@YOUR_HOST
#   cd /var/www/html && bash scripts/container_deploy.sh
#
# Requires a git checkout (see docs/DEPLOY_GIT.md for first-time clone). Server .env is never in git;
# you will be prompted for MN2_WALLET_PASSPHRASE when the terminal is interactive.
set -euo pipefail

REMOTE_BASE="${REMOTE_BASE:-/var/www/html}"
cd "$REMOTE_BASE" || { echo "Missing $REMOTE_BASE"; exit 1; }

echo "=========================================="
echo "GIT DEPLOY (on-server)"
echo "=========================================="
date -Is
echo "Working directory: $PWD"
echo

if [[ ! -d .git ]]; then
  echo "ERROR: $REMOTE_BASE is not a git checkout."
  echo "One-time setup: see docs/DEPLOY_GIT.md"
  exit 1
fi

echo "[1/6] Git sync origin/main..."
git remote -v | head -2 || true
git fetch origin main
git checkout main
git pull --ff-only origin main
echo "  HEAD: $(git log -1 --oneline)"
echo

echo "[2/6] Python dependencies (.venv; never system pip — PEP 668)..."
VENV="$REMOTE_BASE/.venv"
PY="python3"
PIP=""
if [[ -x "$VENV/bin/python" ]]; then
  PY="$VENV/bin/python"
  PIP="$VENV/bin/pip"
elif [[ ! -d "$VENV" ]]; then
  echo "  Creating $VENV ..."
  if python3 -m venv "$VENV" 2>/dev/null; then
    PY="$VENV/bin/python"
    PIP="$VENV/bin/pip"
  else
    echo "  [WARN] could not create venv — pip step skipped"
  fi
fi
REQ=""
for candidate in requirements-production.txt requirements.txt; do # pragma: allowlist secret # pragma: allowlist secret
  if [[ -f "$REMOTE_BASE/$candidate" ]]; then
    REQ="$candidate"
    break
  fi
done
if [[ -n "$PIP" && -n "$REQ" ]]; then
  "$PIP" install --upgrade pip wheel setuptools >/dev/null 2>&1 || true
  if "$PIP" install --no-cache-dir -r "$REQ"; then
    echo "  [OK] $PIP install -r $REQ"
  else
    echo "  [WARN] pip install failed — try: $PIP install -r $REQ"
  fi
  if [[ -n "$(command -v www-data 2>/dev/null || true)" ]] || id www-data >/dev/null 2>&1; then
    chown -R www-data:www-data "$VENV" 2>/dev/null || true
  fi
elif [[ -z "$REQ" ]]; then
  echo "  No requirements file — skipped"
else
  echo "  No .venv pip — skipped (run python3 -m venv $VENV)"
fi
echo

echo "[3/6] MN2 wallet passphrase (.env on server only)..."
ENV_FILE="$REMOTE_BASE/.env"
touch "$ENV_FILE"
if [[ -t 0 ]]; then
  read -rsp "MN2_WALLET_PASSPHRASE (Enter to leave unchanged): " _pw
  echo
  if [[ -n "${_pw:-}" ]]; then
    ENV_FILE="$ENV_FILE" MN2_WALLET_PASSPHRASE="$_pw" python3 - <<'PY'
import os
path = os.environ["ENV_FILE"]
key = "MN2_WALLET_PASSPHRASE"
val = os.environ["MN2_WALLET_PASSPHRASE"]
lines = []
found = False
if os.path.isfile(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
out = []
for line in lines:
    if line.startswith(key + "="):
        out.append(f"{key}={val}")
        found = True
    else:
        out.append(line)
if not found:
    if out and out[-1].strip():
        out.append("")
    out.append(f"# Wallet unlock for getnewaddress (container_deploy.sh)")
    out.append(f"{key}={val}")
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(out).rstrip() + "\n")
print("  Updated MN2_WALLET_PASSPHRASE in .env")
PY
  else
    echo "  Skipped (unchanged)"
  fi
else
  echo "  Non-interactive — set MN2_WALLET_PASSPHRASE in .env manually if needed."
fi
echo

echo "[4/6] Database migrations (idempotent)..."
MIG_PY="python3"
if [[ -x "$REMOTE_BASE/.venv/bin/python" ]]; then
  MIG_PY="$REMOTE_BASE/.venv/bin/python"
fi
if [[ -f "$REMOTE_BASE/scripts/apply_db_migrations.py" ]]; then
  "$MIG_PY" "$REMOTE_BASE/scripts/apply_db_migrations.py" || echo "  [WARN] DB migrations failed — check logs"
else
  echo "  skipped (apply_db_migrations.py missing)"
fi
echo

echo "[5/6] Apply routes / restart uwsgi stack..."
bash "$REMOTE_BASE/scripts/production_apply_routes.sh"  # pragma: allowlist secret
echo

echo "[6/6] Optional Docker sidecars..."
if command -v docker >/dev/null 2>&1 && [[ -f "$REMOTE_BASE/docker/suno-api/docker-compose.yml" ]]; then
  bash "$REMOTE_BASE/scripts/setup_suno_proxy.sh" "$REMOTE_BASE" || echo "  [WARN] suno proxy setup failed (non-fatal)"
else
  echo "  Docker or docker/suno-api not present — skipped."
fi

echo
echo "=========================================="
echo "GIT DEPLOY COMPLETE"
echo "=========================================="
for path in /api/health /api/version; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:5000${path}" 2>/dev/null || echo "000")
  echo "  ${path}: HTTP ${code}"
done

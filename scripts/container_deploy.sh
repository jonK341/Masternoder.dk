#!/usr/bin/env bash
# Deploy on the live server host (bare metal, VM, or LXC — run *inside* the app environment). <!-- pragma: allowlist secret -->
#
# Typical: ssh root@YOUR_HOST
#          cd /var/www/html && bash scripts/container_deploy.sh
#
# Does NOT upload from your laptop; syncs code via git when .git exists, then restarts app
# services. Set MN2_WALLET_PASSPHRASE interactively when prompted (not stored in git).
set -euo pipefail

REMOTE_BASE="${REMOTE_BASE:-/var/www/html}"
cd "$REMOTE_BASE" || { echo "Missing $REMOTE_BASE"; exit 1; }

echo "=========================================="
echo "CONTAINER DEPLOY (on-server)"
echo "=========================================="
date -Is
echo "Working directory: $PWD"
echo

if [[ -d .git ]]; then
  echo "[1/4] Git sync origin/main..."
  git fetch origin main
  git checkout main
  git pull --ff-only origin main
else
  echo "[1/4] No .git in $REMOTE_BASE — skip git pull."
  echo "      Upload code first (e.g. python scripts/deploy.py … from a machine with SSH)."
fi
echo

echo "[2/4] MN2 wallet passphrase (.env on server only)..."
ENV_FILE="$REMOTE_BASE/.env"
touch "$ENV_FILE"
if [[ -t 0 ]]; then
  read -rsp "MN2_WALLET_PASSPHRASE (Enter to leave unchanged): " _pw
  echo
  if [[ -n "${_pw:-}" ]]; then
    if grep -q '^MN2_WALLET_PASSPHRASE=' "$ENV_FILE" 2>/dev/null; then
      sed -i.bak "s|^MN2_WALLET_PASSPHRASE=.*|MN2_WALLET_PASSPHRASE=${_pw}|" "$ENV_FILE"
    else
      printf '\n# Wallet unlock for getnewaddress (container_deploy.sh)\nMN2_WALLET_PASSPHRASE=%s\n' "$_pw" >> "$ENV_FILE"
    fi
    echo "  Updated MN2_WALLET_PASSPHRASE in .env"
  else
    echo "  Skipped (unchanged)"
  fi
else
  echo "  Non-interactive session — set MN2_WALLET_PASSPHRASE in .env manually if needed."
fi
echo

echo "[3/4] Apply routes / restart uwsgi stack..."
bash "$REMOTE_BASE/scripts/production_apply_routes.sh"  # pragma: allowlist secret
echo

echo "[4/4] Optional Docker sidecars..."
if command -v docker >/dev/null 2>&1 && [[ -f "$REMOTE_BASE/docker/suno-api/docker-compose.yml" ]]; then
  bash "$REMOTE_BASE/scripts/setup_suno_proxy.sh" "$REMOTE_BASE" || echo "  [WARN] suno proxy setup failed (non-fatal)"
else
  echo "  Docker or docker/suno-api not present — skipped."
fi

echo
echo "=========================================="
echo "CONTAINER DEPLOY COMPLETE"
echo "=========================================="
echo "Smoke: curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/api/health"

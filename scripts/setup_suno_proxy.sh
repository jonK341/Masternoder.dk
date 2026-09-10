#!/usr/bin/env bash
# Bootstrap self-hosted Suno proxy on production (Docker).
# Run on server as root or a user in the docker group.
set -euo pipefail

ROOT="${1:-/var/www/html}"
COMPOSE_DIR="$ROOT/docker/suno-api"
ENV_FILE="$COMPOSE_DIR/.env"
SITE_ENV="$ROOT/.env"

echo "[suno] Checking Docker..."
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not installed. Install Docker Engine first."
  exit 1
fi

mkdir -p "$COMPOSE_DIR"
if [ ! -f "$COMPOSE_DIR/docker-compose.yml" ]; then
  echo "ERROR: $COMPOSE_DIR/docker-compose.yml missing — deploy repo first."
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  cp "$COMPOSE_DIR/.env.example" "$ENV_FILE"
  echo "[suno] Created $ENV_FILE — edit SUNO_COOKIE before starting."
fi

if ! grep -q '^SUNO_COOKIE=.\+' "$ENV_FILE" 2>/dev/null; then
  echo "WARN: SUNO_COOKIE is empty in $ENV_FILE"
  echo "      Get cookie from suno.com → DevTools → Cookies → __client"
fi

echo "[suno] Starting proxy on 127.0.0.1:3000..."
docker compose -f "$COMPOSE_DIR/docker-compose.yml" up -d

echo "[suno] Proxy status:"
docker compose -f "$COMPOSE_DIR/docker-compose.yml" ps

if [ -f "$SITE_ENV" ]; then
  if ! grep -q '^SUNO_API_BASE=' "$SITE_ENV"; then
    echo "" >> "$SITE_ENV"
    echo "# Suno proxy (added by setup_suno_proxy.sh)" >> "$SITE_ENV"
    echo "SUNO_API_BASE=http://127.0.0.1:3000" >> "$SITE_ENV"
    echo "[suno] Added SUNO_API_BASE to $SITE_ENV"
  fi
  if ! grep -q '^SUNO_API_KEY=' "$SITE_ENV"; then
    echo "SUNO_API_KEY=local" >> "$SITE_ENV"
    echo "[suno] Added SUNO_API_KEY=local to $SITE_ENV (proxy may not require auth)"
  fi
  echo "[suno] Restart uwsgi: systemctl restart uwsgi-vidgenerator"
else
  echo "WARN: $SITE_ENV not found — add SUNO_API_BASE and SUNO_API_KEY manually"
fi

echo "[suno] Verify: curl -s http://127.0.0.1:3000/ | head"
echo "[suno] Then: curl -s https://masternoder.dk/api/creator/music/status"

#!/usr/bin/env bash
# Pull camgirls studio expansion files from GitHub (PR branch) onto the server.
# Usage (on server): cd /var/www/html && bash scripts/camgirls_prod_fast_sync.sh
set -euo pipefail
WEB="${WEB_ROOT:-/var/www/html}"
BRANCH="${CAMGIRLS_SYNC_BRANCH:-pr/camgirls-studio-expansion}"
BASE="https://raw.githubusercontent.com/jonK341/Masternoder.dk/${BRANCH}"
cd "$WEB"
FILES=(
  backend/services/camgirls_service.py
  backend/services/camgirls_payout_service.py
  backend/services/camgirls_social_service.py
  backend/services/camgirls_studio_service.py
  backend/services/camgirls_status_service.py
  backend/services/camgirls_catalog_db_service.py
  backend/services/camgirls_agents_service.py
  backend/routes/camgirls_routes.py
  backend/routes/all_page_routes.py
  backend/routes/monetization_expansion_routes.py
  data/camgirls_performers.json
  data/camgirls_agent_models.json
  data/camgirls_studio_catalog.json
  data/camgirls_next_todos.json
  camgirls/index.html
  camgirls/performer.html
  static/js/camgirls.js
  static/js/camgirls-studio.js
  static/js/camgirls-stream-voice.js
  static/js/command-center-hub.js
  scripts/camgirls_onboard_performers.py
  scripts/camgirls_provision_payout_addresses.py
  scripts/camgirls_post_deploy_verify.py
)
AVATARS=(aurora jade velvet skylar rio mist honey storm pixie venus)
for a in "${AVATARS[@]}"; do
  FILES+=("static/camgirls/avatar-${a}.svg")
done
echo "[camgirls_prod_fast_sync] branch=${BRANCH} web=${WEB}"
for f in "${FILES[@]}"; do
  mkdir -p "$(dirname "$f")"
  curl -fsSL -o "$f" "${BASE}/${f}"
  echo "  OK $f"
done
echo "[camgirls_prod_fast_sync] restart uwsgi if needed, then:"
echo "  bash scripts/camgirls_py.sh scripts/camgirls_provision_payout_addresses.py"
echo "  bash scripts/camgirls_py.sh scripts/camgirls_post_deploy_verify.py --remote-only"

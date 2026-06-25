#!/usr/bin/env bash
# Casino production ID/deploy checklist (no secrets). See docs/CASINO_DEPLOY_OPS.md
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ok() { printf '[ ] %s\n' "$*"; }

echo "MasterNoder Casino - ops checklist (package: dk.masternoder.casino)"
echo "Full commands: docs/CASINO_DEPLOY_OPS.md"
echo ""

echo "== Local =="
ok "pytest tests/unit/test_casino_*.py (or full tests/)"
ok "python scripts/deploy.py casino --list-files"
ok "Replace REPLACE_WITH_PLAY_APP_SIGNING_SHA256 in static/.well-known/assetlinks.json"
ok "Replace TEAMID in static/.well-known/apple-app-site-association"
echo ""

echo "== Deploy =="
ok "python scripts/deploy.py casino --ask-pass"
ok "python scripts/deploy.py --files static/.well-known/* --upload-only --ask-pass"
ok "Server: sync static/.well-known to /.well-known if nginx requires root path"
echo ""

echo "== Server .env (/var/www/html/.env) =="
ok "DISCORD_CHANNEL_ID_CASINO=https://discord.com/api/webhooks/... (full URL)"
ok "DISCORD_OPS_SECRET=<random> (cron + fan-out API)"
ok "META_PIXEL_ID=... (optional)"
ok "systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001 after .env changes"
echo ""

echo "== Cron =="
ok "chmod +x /var/www/html/cron/discord_casino_fanout.sh"
ok "crontab: */5 * * * * /var/www/html/cron/discord_casino_fanout.sh"
echo ""

echo "== After store approval =="
ok "data/casino_config.json mobile.app_store_url - real App Store link"
ok "Redeploy data/casino_config.json"
echo ""

echo "== Verify =="
ok "curl https://masternoder.dk/api/casino/mobile/config"
ok "curl https://masternoder.dk/.well-known/assetlinks.json"
ok "POST /api/discord/casino/fanout with dry_run=true"
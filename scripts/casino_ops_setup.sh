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
ok "python scripts/casino_play_assetlinks_update.py \"<Play App Signing SHA-256>\""
ok "Replace TEAMID in static/.well-known/apple-app-site-association"
echo ""

echo "== Deploy =="
ok "python scripts/deploy.py casino --ask-pass"
ok "python scripts/deploy.py well_known --upload-only --ask-pass  (syncs to /.well-known/)"
echo ""

echo "== Server .env (/var/www/html/.env) =="
echo "  Remote audit (uses DEPLOY_KEY_PATH from .env):"
echo "    python scripts/casino_ops_remote.py --audit"
echo "    python scripts/casino_ops_remote.py --ensure-ops-secret --reload"
echo "    python scripts/casino_ops_remote.py --discord-casino-webhook https://discord.com/api/webhooks/... --reload"
echo ""
ok "DISCORD_CHANNEL_ID_CASINO=https://discord.com/api/webhooks/... (full URL)"
ok "DISCORD_OPS_SECRET=<random> (cron + fan-out API) — auto: --ensure-ops-secret"
ok "META_PIXEL_ID=... (optional) — --meta-pixel-id ID"
ok "systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001 after .env changes — use --reload"
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
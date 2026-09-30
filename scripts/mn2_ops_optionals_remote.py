#!/usr/bin/env python3
"""
MN2 optional ops — env audit, secret bootstrap, cron verify, API smoke (one SSH session).

  python scripts/mn2_ops_optionals_remote.py --ask-pass --audit
  python scripts/mn2_ops_optionals_remote.py --ask-pass --ensure-secrets --reload
  python scripts/mn2_ops_optionals_remote.py --ask-pass --all
  python scripts/mn2_ops_optionals_remote.py --ask-pass --livekit-url wss://... --livekit-api-key ... --livekit-api-secret ...

Does NOT upload local .env wholesale. Only appends missing keys (with timestamped backup).
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user, require_deploy_pass

WEB = "/var/www/html"

# Keys we can auto-generate on the server (openssl rand -hex 24)
AUTO_SECRET_KEYS = (
    "AGENT_CRON_SECRET",
    "COGS_ADMIN_REPORT_KEY",
)

# Manual / external setup — audit only unless CLI flags provided
MANUAL_KEYS = (
    "NOTIFY_ADMIN_EMAIL",
    "NOTIFY_SMTP_HOST",
    "NOTIFY_SMTP_USER",
    "NOTIFY_SMTP_PASSWORD",
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "DISCORD_CHANNEL_ID_MARKET",
    "DISCORD_WEBHOOK_URL",
)


def sh(ssh, cmd: str, timeout: int = 120) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    if err:
        out = (out + "\n[stderr] " + err).strip() if out else "[stderr] " + err
    return out


def _remote_audit_script() -> str:
    keys = list(AUTO_SECRET_KEYS) + list(MANUAL_KEYS)
    keys_shell = " ".join(keys)
    return rf'''bash -s <<'ENDSCRIPT'
set +e
cd {WEB}
ENV=".env"
echo "== .env optional keys audit =="
for k in {keys_shell}; do
  line=$(grep -E "^${{k}}=" "$ENV" 2>/dev/null | tail -1 || true)
  val="${{line#*=}}"
  val=$(echo "$val" | tr -d '\r"' | xargs)
  if [ -n "$val" ]; then
    echo "OK   $k (set)"
  else
    echo "MISS $k"
  fi
done

echo ""
echo "== installed monetization/discord crons =="
for f in masternoder-monetization masternoder-revenue-pulse masternoder-margin-report masternoder-discord-market masternoder-discord-promo; do
  if [ -f "/etc/cron.d/$f" ]; then echo "OK   /etc/cron.d/$f"; else echo "MISS /etc/cron.d/$f"; fi
done
ENDSCRIPT'''


def _remote_ensure_secrets_script(extra_lines: list[str]) -> str:
    extra = "\n".join(extra_lines)
    auto = " ".join(AUTO_SECRET_KEYS)
    return rf'''bash -s <<'ENDSCRIPT'
set -e
cd {WEB}
ENV=".env"
BK=".env.bak.$(date -u +%Y%m%dT%H%M%SZ)"
cp "$ENV" "$BK"
echo "backup: $BK"

rand_hex() {{ openssl rand -hex 24; }}

for k in {auto}; do
  line=$(grep -E "^${{k}}=" "$ENV" 2>/dev/null | tail -1 || true)
  val="${{line#*=}}"
  val=$(echo "$val" | tr -d '\r"' | xargs)
  if [ -z "$val" ]; then
    echo "${{k}}=$(rand_hex)" >> "$ENV"
    echo "ADD  $k"
  else
    echo "KEEP $k"
  fi
done

{extra}

echo "done ensure-secrets"
ENDSCRIPT'''


def _remote_install_crons_script() -> str:
    return rf'''bash -s <<'ENDSCRIPT'
set +e
cd {WEB}
install_cron() {{
  local script="$1" cron_d="$2" name="$3"
  chmod +x "$script" 2>/dev/null || true
  if [ -f "$cron_d" ]; then
    cp "$cron_d" "/etc/cron.d/$name"
    chmod 644 "/etc/cron.d/$name"
    echo "OK   $name"
  else
    echo "MISS $cron_d"
  fi
}}
echo "== install crons =="
install_cron cron/monetization_cron.sh cron/masternoder-monetization.cron.d masternoder-monetization
install_cron cron/revenue_pulse_cron.sh cron/masternoder-revenue-pulse.cron.d masternoder-revenue-pulse
install_cron cron/margin_report_cron.sh cron/masternoder-margin-report.cron.d masternoder-margin-report
install_cron cron/discord_market_fanout.sh cron/masternoder-discord-market.cron.d masternoder-discord-market
install_cron cron/discord_promo_rotator.sh cron/masternoder-discord-promo.cron.d masternoder-discord-promo
ENDSCRIPT'''


def _remote_reload_script() -> str:
    return r'''bash -s <<'ENDSCRIPT'
set +e
echo "== reload app (pick up .env) =="
systemctl restart python-proxy 2>&1 || true
sleep 4
systemctl restart uwsgi-vidgenerator 2>&1 || true
sleep 6
systemctl is-active python-proxy uwsgi-vidgenerator 2>&1
ENDSCRIPT'''


def _remote_verify_script() -> str:
    return rf'''bash -s <<'ENDSCRIPT'
set +e
cd {WEB}
ENV=".env"
get_env() {{ grep -E "^$1=" "$ENV" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r"' | xargs; }}

echo "== API smoke (localhost) =="

CODE=$(curl -sS -m 15 -o /tmp/_lk.json -w '%{{http_code}}' http://127.0.0.1:5000/api/camgirls/livekit/status 2>/dev/null || echo 000)
echo "livekit/status HTTP $CODE"
grep -o '"mode":"[^"]*"' /tmp/_lk.json 2>/dev/null || head -c 120 /tmp/_lk.json 2>/dev/null; echo

KEY=$(get_env COGS_ADMIN_REPORT_KEY)
if [ -n "$KEY" ]; then
  CODE=$(curl -sS -m 20 -o /tmp/_mr.json -w '%{{http_code}}' -H "X-Cogs-Admin-Key: $KEY" \
    "http://127.0.0.1:5000/api/monetization/report?since_days=7" 2>/dev/null || echo 000)
  echo "monetization/report HTTP $CODE"
  python3 -c "import json;d=json.load(open('/tmp/_mr.json'));print('  revenue_usd',d.get('revenue_usd_total'),'margin',d.get('blended_gross_margin_vs_metering'))" 2>/dev/null || head -c 120 /tmp/_mr.json
else
  echo "SKIP monetization/report (no COGS_ADMIN_REPORT_KEY)"
fi

TOKEN=$(get_env AGENT_CRON_SECRET)
if [ -n "$TOKEN" ]; then
  CODE=$(curl -sS -m 25 -o /tmp/_cron.json -w '%{{http_code}}' -X POST -H "X-Agent-Cron-Token: $TOKEN" \
    "http://127.0.0.1:5000/api/agents/cron/run?jobs=monetization_weekly_revenue_pulse" 2>/dev/null || echo 000)
  echo "cron revenue_pulse HTTP $CODE"
  head -c 200 /tmp/_cron.json 2>/dev/null; echo
else
  echo "SKIP agent cron (no AGENT_CRON_SECRET)"
fi

MARKET=$(get_env DISCORD_CHANNEL_ID_MARKET)
if [ -n "$MARKET" ]; then
  if echo "$MARKET" | grep -q '^https://'; then echo "OK   DISCORD_CHANNEL_ID_MARKET looks like webhook URL"; else echo "WARN DISCORD_CHANNEL_ID_MARKET should be full webhook URL not channel id"; fi
else
  echo "MISS DISCORD_CHANNEL_ID_MARKET (market fan-out 403 until set)"
fi
ENDSCRIPT'''


def _shell_export(key: str, value: str) -> str:
    safe = (value or "").replace("'", "'\"'\"'")
    return f"""if ! grep -qE '^{key}=' "$ENV" 2>/dev/null || [ -z "$(grep -E '^{key}=' "$ENV" | tail -1 | cut -d= -f2- | tr -d '\\r\"' | xargs)" ]; then
  echo '{key}={safe}' >> "$ENV"
  echo "ADD  {key}"
else
  echo "KEEP {key}"
fi"""


def main() -> int:
    p = argparse.ArgumentParser(description="MN2 optional ops: env + crons + smoke")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--audit", action="store_true", help="Audit .env keys and crons only")
    p.add_argument("--ensure-secrets", action="store_true", help="Generate missing AGENT_CRON_SECRET + COGS_ADMIN_REPORT_KEY on server")
    p.add_argument("--install-crons", action="store_true", help="Install monetization + discord crons")
    p.add_argument("--reload", action="store_true", help="Restart python-proxy + uwsgi-vidgenerator after .env changes")
    p.add_argument("--verify", action="store_true", help="Localhost API smoke on server")
    p.add_argument("--all", action="store_true", help="ensure-secrets + install-crons + reload + verify")
    p.add_argument("--notify-email", help="Set NOTIFY_ADMIN_EMAIL on server if missing")
    p.add_argument("--livekit-url")
    p.add_argument("--livekit-api-key")
    p.add_argument("--livekit-api-secret")
    p.add_argument("--discord-market-webhook", help="Full Discord webhook URL for #market")
    args = p.parse_args()

    if args.all:
        args.audit = True
        args.ensure_secrets = True
        args.install_crons = True
        args.reload = True
        args.verify = True

    if not any([args.audit, args.ensure_secrets, args.install_crons, args.reload, args.verify, args.all]):
        args.audit = True

    extra_lines: list[str] = []
    if args.notify_email:
        extra_lines.append(_shell_export("NOTIFY_ADMIN_EMAIL", args.notify_email.strip()))
    if args.livekit_url:
        extra_lines.append(_shell_export("LIVEKIT_URL", args.livekit_url.strip()))
    if args.livekit_api_key:
        extra_lines.append(_shell_export("LIVEKIT_API_KEY", args.livekit_api_key.strip()))
    if args.livekit_api_secret:
        extra_lines.append(_shell_export("LIVEKIT_API_SECRET", args.livekit_api_secret.strip()))
    if args.discord_market_webhook:
        extra_lines.append(_shell_export("DISCORD_CHANNEL_ID_MARKET", args.discord_market_webhook.strip()))

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh, auth_method, _ = connect_deploy_ssh(pw)
    print(f"== Connected {deploy_user()}@{deploy_host()} ({auth_method}) ==\n")

    if args.audit:
        print(sh(ssh, _remote_audit_script(), timeout=60))
        print()

    if args.ensure_secrets or extra_lines:
        print("== ensure secrets / optional env ==")
        print(sh(ssh, _remote_ensure_secrets_script(extra_lines), timeout=60))
        print()

    if args.install_crons:
        print("== install crons ==")
        print(sh(ssh, _remote_install_crons_script(), timeout=60))
        print()

    if args.reload:
        print(sh(ssh, _remote_reload_script(), timeout=90))
        print()

    if args.verify:
        print(sh(ssh, _remote_verify_script(), timeout=90))
        print()

    ssh.close()
    print("Optionals pass complete.")
    print("Manual: LIVEKIT_* from https://cloud.livekit.io — NOTIFY_SMTP_* for weekly emails.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

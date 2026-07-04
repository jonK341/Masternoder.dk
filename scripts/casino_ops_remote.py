#!/usr/bin/env python3
"""
Casino production ops — audit server .env, bootstrap secrets, cron, reload.

Uses DEPLOY_KEY_PATH from .env (same as deploy.py / mn2_ops_optionals_remote.py).

  python scripts/casino_ops_remote.py --audit
  python scripts/casino_ops_remote.py --ensure-ops-secret --reload
  python scripts/casino_ops_remote.py --discord-casino-webhook https://discord.com/api/webhooks/... --reload
  python scripts/casino_ops_remote.py --meta-pixel-id 123456789 --reload
  python scripts/casino_ops_remote.py --all

Does NOT upload local .env wholesale. Only appends missing keys (timestamped backup).
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user, require_deploy_pass

WEB = "/var/www/html"

CASINO_ENV_KEYS = (
    "DISCORD_CHANNEL_ID_CASINO",
    "DISCORD_OPS_SECRET",
    "AGENT_CASINO_SECRET",
    "META_PIXEL_ID",
)

AUTO_SECRET_KEYS = ("DISCORD_OPS_SECRET",)


def sh(ssh, cmd: str, timeout: int = 120) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    if err:
        out = (out + "\n[stderr] " + err).strip() if out else "[stderr] " + err
    return out


def _remote_audit_script() -> str:
    keys_shell = " ".join(CASINO_ENV_KEYS)
    return rf'''bash -s <<'ENDSCRIPT'
set +e
cd {WEB}
ENV=".env"
echo "== Server .env ($ENV) =="
for k in {keys_shell}; do
  line=$(grep -E "^${{k}}=" "$ENV" 2>/dev/null | tail -1 || true)
  val="${{line#*=}}"
  val=$(echo "$val" | tr -d '\r"' | xargs)
  if [ -n "$val" ]; then
    if [ "$k" = "DISCORD_CHANNEL_ID_CASINO" ]; then
      if echo "$val" | grep -q '^https://discord.com/api/webhooks/'; then
        echo "OK   $k (webhook URL)"
      else
        echo "WARN $k (set but not a full discord webhook URL)"
      fi
    elif [ "$k" = "META_PIXEL_ID" ]; then
      echo "OK   $k (optional, set)"
    else
      echo "OK   $k (set)"
    fi
  else
    if [ "$k" = "META_PIXEL_ID" ]; then
      echo "SKIP $k (optional)"
    else
      echo "MISS $k"
    fi
  fi
done

echo ""
echo "== Cron =="
if [ -x cron/discord_casino_fanout.sh ]; then
  echo "OK   cron/discord_casino_fanout.sh executable"
else
  echo "MISS cron/discord_casino_fanout.sh executable"
fi
if crontab -l 2>/dev/null | grep -q discord_casino_fanout; then
  echo "OK   root crontab has discord_casino_fanout"
elif [ -f /etc/cron.d/masternoder-discord-casino ]; then
  echo "OK   /etc/cron.d/masternoder-discord-casino"
else
  echo "MISS casino fan-out cron (*/5 recommended)"
fi
if [ -f /etc/cron.d/masternoder-casino-revenue ]; then
  echo "OK   /etc/cron.d/masternoder-casino-revenue"
else
  echo "MISS casino daily revenue cron"
fi

echo ""
echo "== Agent API (localhost) =="
CODE=$(curl -sS -m 10 -o /tmp/_cas_ag.json -w '%{{http_code}}' http://127.0.0.1:5000/api/agent/casino/models 2>/dev/null || echo 000)
echo "agent/casino/models HTTP $CODE"

echo ""
echo "== uwsgi =="
systemctl is-active uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>&1 | sed 's/^/     /'
ENDSCRIPT'''


def _shell_export(key: str, value: str) -> str:
    safe = (value or "").replace("'", "'\"'\"'")
    return f"""if ! grep -qE '^{key}=' "$ENV" 2>/dev/null || [ -z "$(grep -E '^{key}=' "$ENV" | tail -1 | cut -d= -f2- | tr -d '\\r\"' | xargs)" ]; then
  echo '{key}={safe}' >> "$ENV"
  echo "ADD  {key}"
else
  echo "KEEP {key}"
fi"""


def _remote_ensure_script(extra_lines: list[str]) -> str:
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

echo "done ensure-env"
ENDSCRIPT'''


def _remote_install_cron_script() -> str:
    return rf'''bash -s <<'ENDSCRIPT'
set -e
cd {WEB}
chmod +x cron/discord_casino_fanout.sh
cat > /etc/cron.d/masternoder-discord-casino <<'CRON'
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
*/5 * * * * root /var/www/html/cron/discord_casino_fanout.sh >> /var/log/masternoder-discord-casino.log 2>&1
CRON
chmod 644 /etc/cron.d/masternoder-discord-casino
echo "OK   /etc/cron.d/masternoder-discord-casino"
ENDSCRIPT'''


def _remote_install_revenue_cron_script() -> str:
    return rf'''bash -s <<'ENDSCRIPT'
set -e
cd {WEB}
chmod +x cron/casino_daily_revenue_report.sh
cat > /etc/cron.d/masternoder-casino-revenue <<'CRON'
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
# Daily 09:05 UTC — dry_run=1 until DISCORD_OPS_WEBHOOK_URL is set for posting
5 9 * * * root CASINO_REVENUE_DRY_RUN=1 /var/www/html/cron/casino_daily_revenue_report.sh >> /var/log/masternoder-casino-revenue.log 2>&1
CRON
chmod 644 /etc/cron.d/masternoder-casino-revenue
echo "OK   /etc/cron.d/masternoder-casino-revenue"
ENDSCRIPT'''


def _remote_reload_script() -> str:
    return r'''bash -s <<'ENDSCRIPT'
set +e
echo "== reload app (pick up .env) =="
systemctl restart python-proxy 2>&1 || true
sleep 3
systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>&1 || true
sleep 6
systemctl is-active python-proxy uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>&1
ENDSCRIPT'''


def _remote_verify_script() -> str:
    return rf'''bash -s <<'ENDSCRIPT'
set +e
cd {WEB}
ENV=".env"
get_env() {{ grep -E "^$1=" "$ENV" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r"' | xargs; }}

echo "== API smoke (localhost) =="
CODE=$(curl -sS -m 15 -o /tmp/_cas_mob.json -w '%{{http_code}}' http://127.0.0.1:5000/api/casino/mobile/config 2>/dev/null || echo 000)
echo "casino/mobile/config HTTP $CODE"
head -c 120 /tmp/_cas_mob.json 2>/dev/null; echo

SECRET=$(get_env DISCORD_OPS_SECRET)
if [ -z "$SECRET" ]; then SECRET=$(get_env MN2_OPS_SECRET); fi
if [ -n "$SECRET" ]; then
  CODE=$(curl -sS -m 20 -o /tmp/_cas_fan.json -w '%{{http_code}}' -X POST \
    -H "X-Ops-Secret: $SECRET" -H "Content-Type: application/json" \
    -d '{{"dry_run":true}}' http://127.0.0.1:5000/api/discord/casino/fanout 2>/dev/null || echo 000)
  echo "discord/casino/fanout dry_run HTTP $CODE"
  head -c 160 /tmp/_cas_fan.json 2>/dev/null; echo
else
  echo "SKIP fan-out (no DISCORD_OPS_SECRET)"
fi

CODE=$(curl -sS -m 15 -o /tmp/_cas_soc.json -w '%{{http_code}}' http://127.0.0.1:5000/api/casino/social/links 2>/dev/null || echo 000)
echo "casino/social/links HTTP $CODE"
python3 -c "import json;d=json.load(open('/tmp/_cas_soc.json'));print('  pixel_id',d.get('pixel_id') or (d.get('facebook') or {{}}).get('pixel_id'))" 2>/dev/null || true

CODE=$(curl -sS -m 15 -o /tmp/_cas_mod.json -w '%{{http_code}}' http://127.0.0.1:5000/api/agent/casino/models 2>/dev/null || echo 000)
echo "agent/casino/models HTTP $CODE"
python3 -c "import json;d=json.load(open('/tmp/_cas_mod.json'));m=d.get('models') if isinstance(d,dict) else [];print('  models',len(m) if isinstance(m,list) else d.get('success',d))" 2>/dev/null || head -c 80 /tmp/_cas_mod.json 2>/dev/null; echo

AGENT_KEY=$(get_env AGENT_CASINO_SECRET)
if [ -n "$AGENT_KEY" ]; then
  CODE=$(curl -sS -m 30 -o /tmp/_cas_run.json -w '%{{http_code}}' -X POST \
    -H "X-Agent-Casino-Key: $AGENT_KEY" -H "Content-Type: application/json" \
    -d '{{"dry_run":true}}' http://127.0.0.1:5000/api/agent/casino/run-all 2>/dev/null || echo 000)
  echo "agent/casino/run-all dry_run HTTP $CODE"
  head -c 200 /tmp/_cas_run.json 2>/dev/null; echo
else
  echo "SKIP agent run-all (no AGENT_CASINO_SECRET)"
fi
ENDSCRIPT'''


def main() -> int:
    p = argparse.ArgumentParser(description="Casino ops: server .env audit + secrets + cron")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--audit", action="store_true", help="Audit casino .env keys + cron")
    p.add_argument(
        "--ensure-ops-secret",
        action="store_true",
        help="Generate DISCORD_OPS_SECRET on server if missing",
    )
    p.add_argument("--discord-casino-webhook", help="Full #casino Discord webhook URL")
    p.add_argument("--meta-pixel-id", help="Optional META_PIXEL_ID value")
    p.add_argument("--install-cron", action="store_true", help="Install /etc/cron.d/masternoder-discord-casino")
    p.add_argument(
        "--install-revenue-cron",
        action="store_true",
        help="Install /etc/cron.d/masternoder-casino-revenue (daily dry_run report)",
    )
    p.add_argument(
        "--reload",
        action="store_true",
        help="Restart uwsgi-vidgenerator + uwsgi-vidgenerator-5001 after .env changes",
    )
    p.add_argument("--verify", action="store_true", help="Localhost casino API smoke")
    p.add_argument(
        "--all",
        action="store_true",
        help="ensure-ops-secret + install-cron + install-revenue-cron + reload + verify (and audit)",
    )
    args = p.parse_args()

    if args.all:
        args.audit = True
        args.ensure_ops_secret = True
        args.install_cron = True
        args.install_revenue_cron = True
        args.reload = True
        args.verify = True

    if not any(
        [
            args.audit,
            args.ensure_ops_secret,
            args.install_cron,
            args.install_revenue_cron,
            args.reload,
            args.verify,
            args.discord_casino_webhook,
            args.meta_pixel_id,
            args.all,
        ]
    ):
        args.audit = True

    extra_lines: list[str] = []
    if args.discord_casino_webhook:
        extra_lines.append(
            _shell_export("DISCORD_CHANNEL_ID_CASINO", args.discord_casino_webhook.strip())
        )
    if args.meta_pixel_id:
        extra_lines.append(_shell_export("META_PIXEL_ID", args.meta_pixel_id.strip()))

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh, auth_method, _ = connect_deploy_ssh(pw)
    print(f"== Connected {deploy_user()}@{deploy_host()} ({auth_method}) ==\n")

    if args.audit:
        print(sh(ssh, _remote_audit_script(), timeout=60))
        print()

    if args.ensure_ops_secret or extra_lines:
        print("== ensure server .env ==")
        print(sh(ssh, _remote_ensure_script(extra_lines), timeout=60))
        print()

    if args.install_cron:
        print("== install discord cron ==")
        print(sh(ssh, _remote_install_cron_script(), timeout=60))
        print()

    if args.install_revenue_cron:
        print("== install revenue cron ==")
        print(sh(ssh, _remote_install_revenue_cron_script(), timeout=60))
        print()

    if args.reload:
        print(sh(ssh, _remote_reload_script(), timeout=120))
        print()

    if args.verify:
        print(sh(ssh, _remote_verify_script(), timeout=90))
        print()

    ssh.close()
    print("Casino ops complete.")
    print("Manual: paste #casino webhook -> --discord-casino-webhook https://discord.com/api/webhooks/...")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
MN2 P1 monetization ops — Pro plan env, webhook id, tier enforcement, smoke.

  python scripts/mn2_p1_monetization_remote.py --ask-pass --audit
  python scripts/mn2_p1_monetization_remote.py --ask-pass --enable-tier-enforcement --reload --verify
  python scripts/mn2_p1_monetization_remote.py --ask-pass --paypal-plan-pro P-5ABC... --paypal-webhook-id WH-... --reload --verify
  python scripts/mn2_p1_monetization_remote.py --ask-pass --all --paypal-plan-pro P-... --paypal-webhook-id WH-...

Does NOT upload local .env wholesale. Appends missing keys only (timestamped backup).
"""
from __future__ import annotations

import argparse
import os
import sys

import paramiko

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

WEB = "/var/www/html"

AUDIT_KEYS = (
    "PAYPAL_SUBSCRIPTION_PLAN_PRO",
    "PAYPAL_SUBSCRIPTION_PLAN_MN_HOST",
    "PAYPAL_WEBHOOK_ID",
    "MONETIZATION_TIER_ENFORCEMENT",
    "PAYPAL_MODE",
    "PAYPAL_CLIENT_ID",
)


def sh(ssh, cmd: str, timeout: int = 120) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    if err:
        out = (out + "\n[stderr] " + err).strip() if out else "[stderr] " + err
    return out


def _shell_export(key: str, value: str) -> str:
    safe = (value or "").replace("'", "'\"'\"'")
    return f"""if ! grep -qE '^{key}=' "$ENV" 2>/dev/null || [ -z "$(grep -E '^{key}=' "$ENV" | tail -1 | cut -d= -f2- | tr -d '\\r\"' | xargs)" ]; then
  echo '{key}={safe}' >> "$ENV"
  echo "ADD  {key}"
else
  sed -i "s|^{key}=.*|{key}={safe}|" "$ENV"
  echo "SET  {key}"
fi"""


def _remote_audit() -> str:
    keys = " ".join(AUDIT_KEYS)
    return rf'''bash -s <<'ENDSCRIPT'
set +e
cd {WEB}
ENV=".env"
echo "== P1 monetization .env audit =="
for k in {keys}; do
  line=$(grep -E "^${{k}}=" "$ENV" 2>/dev/null | tail -1 || true)
  val="${{line#*=}}"
  val=$(echo "$val" | tr -d '\r"' | xargs)
  if [ -n "$val" ]; then
    echo "OK   $k (set)"
  else
    echo "MISS $k"
  fi
done
ENDSCRIPT'''


def _remote_apply(extra_lines: list[str]) -> str:
    extra = "\n".join(extra_lines)
    return rf'''bash -s <<'ENDSCRIPT'
set -e
cd {WEB}
ENV=".env"
BK=".env.bak.$(date -u +%Y%m%dT%H%M%SZ)"
cp "$ENV" "$BK"
echo "backup: $BK"
{extra}
echo "done p1 apply"
ENDSCRIPT'''


def _remote_reload() -> str:
    return r'''bash -s <<'ENDSCRIPT'
set +e
echo "== reload app =="
systemctl restart python-proxy 2>&1 || true
sleep 4
systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>&1 || true
sleep 6
systemctl is-active python-proxy uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>&1
ENDSCRIPT'''


def _remote_verify() -> str:
    return rf'''bash -s <<'ENDSCRIPT'
set +e
cd {WEB}
echo "== P1 API smoke =="
curl -sS -m 20 http://127.0.0.1:5000/api/monetization/config | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('  subscription_pro_live', d.get('subscription_pro_live'))
print('  paypal_webhook_configured', d.get('paypal_webhook_configured'))
print('  tier_enforcement_enabled', d.get('tier_enforcement_enabled'))
plans=(d.get('subscriptions') or {{}}).get('plans') or {{}}
print('  public_plans', len(plans), list(plans.keys())[:3])
" 2>/dev/null || echo "FAIL monetization/config"

CODE=$(curl -sS -m 20 -o /tmp/_promo.json -w '%{{http_code}}' -X POST -H 'Content-Type: application/json' \
  -d '{{"code":"GENERATE10","user_id":"p1_smoke","amount_usd":9.99}}' \
  http://127.0.0.1:5000/api/shop/promo/apply 2>/dev/null || echo 000)
echo "promo/apply GENERATE10 HTTP $CODE"
grep -o '"mode":"[^"]*"' /tmp/_promo.json 2>/dev/null || head -c 120 /tmp/_promo.json 2>/dev/null; echo
ENDSCRIPT'''


def main() -> int:
    p = argparse.ArgumentParser(description="MN2 P1: Pro plan env, webhook, tier enforcement")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--audit", action="store_true")
    p.add_argument("--enable-tier-enforcement", action="store_true")
    p.add_argument("--paypal-plan-pro", help="Set PAYPAL_SUBSCRIPTION_PLAN_PRO=P-…")
    p.add_argument("--paypal-plan-mn-host", help="Set PAYPAL_SUBSCRIPTION_PLAN_MN_HOST=P-…")
    p.add_argument("--paypal-webhook-id", help="Set PAYPAL_WEBHOOK_ID=WH-…")
    p.add_argument("--reload", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--all", action="store_true", help="enable tier enforcement + reload + verify")
    args = p.parse_args()

    if args.all:
        args.enable_tier_enforcement = True
        args.reload = True
        args.verify = True

    if not any([
        args.audit,
        args.enable_tier_enforcement,
        args.paypal_plan_pro,
        args.paypal_plan_mn_host,
        args.paypal_webhook_id,
        args.reload,
        args.verify,
        args.all,
    ]):
        args.audit = True

    extra: list[str] = []
    if args.enable_tier_enforcement:
        extra.append(_shell_export("MONETIZATION_TIER_ENFORCEMENT", "1"))
    if args.paypal_plan_pro:
        extra.append(_shell_export("PAYPAL_SUBSCRIPTION_PLAN_PRO", args.paypal_plan_pro.strip()))
    if args.paypal_plan_mn_host:
        extra.append(_shell_export("PAYPAL_SUBSCRIPTION_PLAN_MN_HOST", args.paypal_plan_mn_host.strip()))
    if args.paypal_webhook_id:
        extra.append(_shell_export("PAYPAL_WEBHOOK_ID", args.paypal_webhook_id.strip()))

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)
    print(f"== Connected {deploy_user()}@{deploy_host()} ==\n")

    if args.audit:
        print(sh(ssh, _remote_audit(), timeout=60))
        print()

    if extra:
        print("== apply P1 env ==")
        print(sh(ssh, _remote_apply(extra), timeout=60))
        print()

    if args.reload:
        print(sh(ssh, _remote_reload(), timeout=90))
        print()

    if args.verify:
        print(sh(ssh, _remote_verify(), timeout=90))
        print()

    ssh.close()
    print("P1 monetization pass complete.")
    print("PayPal dashboard (Live): create Pro plan P-… + webhook WH-… then:")
    print("  python scripts/mn2_p1_monetization_remote.py --ask-pass --paypal-plan-pro P-... --paypal-webhook-id WH-... --enable-tier-enforcement --reload --verify")
    print("Deploy profile + security UI: python scripts/deploy.py static_pages --ask-pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Schedule a graceful production reboot on masternoder.dk (kernel updates pending).

Stops masternoder2d cleanly, then uwsgi/python-proxy, sync, reboot.

Usage:
  python scripts/mn2_schedule_reboot_remote.py --ask-pass
  python scripts/mn2_schedule_reboot_remote.py --ask-pass --when 2026-06-22T04:00:00Z
  python scripts/mn2_schedule_reboot_remote.py --ask-pass --list
  python scripts/mn2_schedule_reboot_remote.py --ask-pass --cancel
  python scripts/mn2_schedule_reboot_remote.py --ask-pass --now   # immediate (maintenance window)
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    import dotenv

    dotenv.load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

REBOOT_SCRIPT = "/usr/local/sbin/mn2-graceful-reboot.sh"
CRON_ONCE = "/etc/cron.d/masternoder-reboot-once"
AT_MARKER = "/var/run/mn2-reboot-scheduled.txt"


def next_sunday_0400_utc(now: datetime | None = None) -> datetime:
    """Next occurrence of Sunday 04:00 UTC (skip if today is Sunday before 04:00)."""
    now = now or datetime.now(timezone.utc)
    target = now.replace(hour=4, minute=0, second=0, microsecond=0)
    # weekday: Mon=0 .. Sun=6
    days_until_sunday = (6 - now.weekday()) % 7
    if days_until_sunday == 0 and now >= target:
        days_until_sunday = 7
    return target + timedelta(days=days_until_sunday)


def parse_when(text: str) -> datetime:
    text = text.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def build_remote_script(*, mode: str, when_iso: str = "") -> str:
    return rf"""bash -s <<'ENDSCRIPT'
set -e
MODE='{mode}'
WHEN_ISO='{when_iso}'
REBOOT_SCRIPT='{REBOOT_SCRIPT}'
CRON_ONCE='{CRON_ONCE}'
AT_MARKER='{AT_MARKER}'

install_reboot_script() {{
  cat > "$REBOOT_SCRIPT" <<'EOF'
#!/bin/bash
set -e
logger -t mn2-reboot "scheduled graceful reboot starting"
systemctl stop masternoder2d 2>/dev/null || true
sleep 12
systemctl stop uwsgi-vidgenerator python-proxy uwsgi vidgenerator-gunicorn 2>/dev/null || true
sleep 3
sync
rm -f /etc/cron.d/masternoder-reboot-once /var/run/mn2-reboot-scheduled.txt 2>/dev/null || true
logger -t mn2-reboot "reboot now"
/sbin/reboot
EOF
  chmod 755 "$REBOOT_SCRIPT"
}}

cancel_scheduled() {{
  rm -f "$CRON_ONCE" "$AT_MARKER" 2>/dev/null || true
  if command -v atq >/dev/null 2>&1; then
    atq 2>/dev/null | awk '{{print $1}}' | while read -r j; do
      atrm "$j" 2>/dev/null || true
    done
  fi
  echo "Cancelled any scheduled MN2 reboot jobs."
}}

list_scheduled() {{
  echo "== pending kernel reboot =="
  if [ -f /var/run/reboot-required ]; then
    cat /var/run/reboot-required 2>/dev/null || echo "(reboot-required present)"
  else
    echo "(no /var/run/reboot-required — kernel may still want reboot after apt)"
  fi
  needrestart -b 2>/dev/null | head -5 || true
  echo ""
  echo "== MN2 schedule marker =="
  if [ -f "$AT_MARKER" ]; then cat "$AT_MARKER"; else echo "(none)"; fi
  echo ""
  echo "== cron once =="
  if [ -f "$CRON_ONCE" ]; then cat "$CRON_ONCE"; else echo "(none)"; fi
  echo ""
  echo "== at queue =="
  atq 2>/dev/null || echo "(atd not running or empty)"
}}

schedule_at() {{
  local when_iso="$1"
  # at -t MMDDhhmmYYYY (minute hour day month year)
  local t
  t=$(date -u -d "$when_iso" +%m%d%H%M%Y 2>/dev/null) || t=$(date -u -d "$when_iso" +%m%d%H%M%Y)
  if ! command -v at >/dev/null 2>&1; then
    return 1
  fi
  systemctl enable --now atd 2>/dev/null || service atd start 2>/dev/null || true
  cancel_scheduled
  install_reboot_script
  echo "$REBOOT_SCRIPT # MN2 scheduled reboot" | at -t "$t"
  echo "$when_iso" > "$AT_MARKER"
  echo "Scheduled via at for $when_iso UTC (at -t $t)"
  atq
  return 0
}}

schedule_cron() {{
  local when_iso="$1"
  local min hour day mon
  min=$(date -u -d "$when_iso" +%-M)
  hour=$(date -u -d "$when_iso" +%-H)
  day=$(date -u -d "$when_iso" +%-d)
  mon=$(date -u -d "$when_iso" +%-m)
  cancel_scheduled
  install_reboot_script
  cat > "$CRON_ONCE" <<EOF
# MN2 one-shot graceful reboot — auto-removed by reboot script
$min $hour $day $mon * root $REBOOT_SCRIPT
EOF
  chmod 644 "$CRON_ONCE"
  echo "$when_iso" > "$AT_MARKER"
  echo "Scheduled via cron for $when_iso UTC ($min $hour $day $mon)"
  cat "$CRON_ONCE"
}}

if [ "$MODE" = "cancel" ]; then
  cancel_scheduled
  exit 0
fi

if [ "$MODE" = "list" ]; then
  list_scheduled
  exit 0
fi

if [ "$MODE" = "now" ]; then
  cancel_scheduled
  install_reboot_script
  echo "Rebooting in 10 seconds (graceful stop)..."
  nohup bash -c 'sleep 10; '"$REBOOT_SCRIPT" > /dev/null 2>&1 &
  echo "OK: reboot initiated in background."
  exit 0
fi

if [ -z "$WHEN_ISO" ]; then
  echo "FAIL: WHEN_ISO empty"
  exit 1
fi

if schedule_at "$WHEN_ISO"; then
  exit 0
fi
echo "WARN: at unavailable — using cron one-shot"
schedule_cron "$WHEN_ISO"
ENDSCRIPT
"""


def main() -> int:
    p = argparse.ArgumentParser(description="Schedule graceful masternoder.dk reboot")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument(
        "--when",
        help="ISO UTC time (default: next Sunday 04:00 UTC), e.g. 2026-06-22T04:00:00Z",
    )
    p.add_argument("--now", action="store_true", help="Reboot in ~10s (graceful stop first)")
    p.add_argument("--list", action="store_true", help="Show pending reboot schedule on server")
    p.add_argument("--cancel", action="store_true", help="Remove scheduled reboot")
    args = p.parse_args()

    if args.cancel:
        mode = "cancel"
        when_iso = ""
    elif args.list:
        mode = "list"
        when_iso = ""
    elif args.now:
        mode = "now"
        when_iso = ""
    else:
        mode = "schedule"
        when = parse_when(args.when) if args.when else next_sunday_0400_utc()
        when_iso = when.strftime("%Y-%m-%dT%H:%M:%SZ")

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    host, user = deploy_host(), deploy_user()
    ssh.connect(host, username=user, password=pw, timeout=30)
    print(f"Connected {user}@{host}\n")

    if mode == "schedule":
        when_dt = parse_when(when_iso)
        print(f"=== Scheduling graceful reboot ===")
        print(f"    When (UTC): {when_iso}")
        print(f"    Local hint: {when_dt.astimezone().strftime('%Y-%m-%d %H:%M %Z')}")
        print(f"    Stops: masternoder2d → uwsgi-vidgenerator → reboot")
        print("")

    script = build_remote_script(mode=mode, when_iso=when_iso)
    _, stdout, stderr = ssh.exec_command(script, get_pty=True, timeout=120)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    print(out)
    if err.strip():
        print(err, file=sys.stderr)
    ssh.close()

    if mode == "schedule" and code == 0:
        print("\nAfter reboot (~2 min downtime):")
        print("  python scripts/mn2_daemon_upgrade_remote.py --ask-pass --verify-post")
        print("  python scripts/mn2_next_ops_remote.py --ask-pass")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

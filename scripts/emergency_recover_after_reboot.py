#!/usr/bin/env python3
"""
Emergency recovery for a CPU-saturated prod host after reboot.

Problem this solves: the 2-vCPU host gets pegged (duplicate app workers +
agent/trading daemons + leftover pytest/ffmpeg), so sshd cannot complete its
protocol banner and the box is unreachable. A plain reboot recurs because the
heavy units auto-start on boot.

Strategy: run this, then trigger a reboot from the Vultr console. This script
hammers reconnect attempts and, on the FIRST successful session (the brief
low-load window early in boot), immediately sheds load by stopping the app +
agent units, captures diagnostics, then restarts nginx + a single uWSGI
instance and verifies local health.

Auth + host resolution reuse deploy_ssh_env (DEPLOY_PASS / DEPLOY_HOST /
DEPLOY_USER from env or project .env).

Usage:
  python3 scripts/emergency_recover_after_reboot.py [--minutes 15] [--interval 4]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from deploy_ssh_env import deploy_host, deploy_user
    HOST = deploy_host()
    USER = deploy_user()
except Exception:  # noqa: BLE001
    HOST = (os.environ.get("DEPLOY_HOST") or "").strip()
    USER = (os.environ.get("DEPLOY_USER") or "root").strip()

# Units that peg the box. Order matters: stop the heaviest / most numerous
# workers first so the CPU frees up enough to finish the rest of recovery.
LOAD_SHED_UNITS = [
    "uwsgi-vidgenerator-5001",
    "python-proxy",
    "uwsgi-vidgenerator",
    "uwsgi",
]


def _pw() -> str:
    pw = (os.environ.get("DEPLOY_PASS") or "").strip()
    if pw:
        return pw
    # Fallback: read from project .env
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(root, ".env")
    if os.path.isfile(env_path):
        for raw in open(env_path, encoding="utf-8"):
            line = raw.strip()
            if line.startswith("DEPLOY_PASS="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    print("DEPLOY_PASS not set (env or .env).", file=sys.stderr)
    sys.exit(1)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _run(ssh, cmd, timeout=25):
    try:
        _in, out, err = ssh.exec_command(cmd, timeout=timeout)
        o = (out.read() or b"").decode(errors="replace").strip()
        e = (err.read() or b"").decode(errors="replace").strip()
        return o, e
    except Exception as ex:  # noqa: BLE001
        return "", f"[exec error] {type(ex).__name__}: {ex}"


def _section(title):
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64, flush=True)


def remediate(ssh) -> None:
    _section(f"[{_now()}] CONNECTED — shedding load first")
    # 1) Stop the CPU hogs immediately (fast, non-blocking issue then confirm).
    for unit in LOAD_SHED_UNITS:
        o, e = _run(ssh, f"systemctl stop {unit} 2>&1 || true", timeout=20)
        print(f"  stop {unit}: {o or e or 'ok'}", flush=True)
    time.sleep(4)

    _section(f"[{_now()}] Load / top CPU consumers")
    o, _ = _run(ssh, "uptime", timeout=15)
    print("uptime:", o)
    o, _ = _run(
        ssh,
        "ps -eo pid,ppid,pcpu,pmem,etimes,comm --sort=-pcpu 2>/dev/null | head -20",
        timeout=20,
    )
    print(o)

    _section(f"[{_now()}] Memory / disk")
    o, _ = _run(ssh, "free -m | head -3", timeout=15)
    print(o)
    o, _ = _run(ssh, "df -h / 2>/dev/null | tail -2", timeout=15)
    print(o)

    _section(f"[{_now()}] Auto-start suspects (timers / running services / cron)")
    o, _ = _run(ssh, "systemctl list-timers --all --no-pager 2>/dev/null | head -25", timeout=20)
    print("--- timers ---\n" + o)
    o, _ = _run(
        ssh,
        "systemctl list-units --type=service --state=running --no-pager 2>/dev/null | head -40",
        timeout=20,
    )
    print("--- running services ---\n" + o)
    o, _ = _run(ssh, "crontab -l 2>/dev/null | grep -vE '^\\s*#' | head -40", timeout=15)
    print("--- root crontab ---\n" + (o or "(empty)"))

    _section(f"[{_now()}] Recent uwsgi / nginx journal")
    o, _ = _run(ssh, "journalctl -u uwsgi-vidgenerator --no-pager -n 15 2>/dev/null", timeout=20)
    print("--- uwsgi-vidgenerator ---\n" + (o or "(none)"))
    o, _ = _run(ssh, "journalctl -u nginx --no-pager -n 8 2>/dev/null", timeout=20)
    print("--- nginx ---\n" + (o or "(none)"))

    _section(f"[{_now()}] Bring web back cleanly")
    o, _ = _run(ssh, "nginx -t 2>&1", timeout=20)
    print("nginx -t:", o)
    o, _ = _run(ssh, "systemctl restart nginx 2>&1 && echo restarted || echo failed", timeout=30)
    print("nginx restart:", o)
    # Start ONE uwsgi instance only (avoid re-saturating the box).
    o, _ = _run(ssh, "systemctl start uwsgi-vidgenerator 2>&1 && echo started || echo failed", timeout=30)
    print("uwsgi-vidgenerator start:", o)
    time.sleep(6)
    o, _ = _run(ssh, "systemctl is-active nginx uwsgi-vidgenerator 2>&1", timeout=15)
    print("is-active (nginx / uwsgi-vidgenerator):\n" + o)
    o, _ = _run(
        ssh,
        "curl -s -m 10 -o /dev/null -w 'local health: %{http_code} in %{time_total}s' http://127.0.0.1:5000/api/health 2>&1",
        timeout=20,
    )
    print(o)
    o, _ = _run(ssh, "uptime", timeout=15)
    print("post-recovery uptime:", o)

    _section(f"[{_now()}] DONE — heavy agent/5001 units left STOPPED on purpose")
    print(
        "Re-enable agent/trading daemons one at a time while watching `top`.\n"
        "If a systemd timer or @reboot cron auto-starts them, disable it to break the loop."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=15.0, help="max time to keep trying")
    ap.add_argument("--interval", type=float, default=4.0, help="seconds between attempts")
    args = ap.parse_args()

    pw = _pw()
    deadline = time.time() + args.minutes * 60
    attempt = 0
    print(f"Target {USER}@{HOST}. Trying for up to {args.minutes:g} min.")
    print(">>> Trigger the Vultr console REBOOT now; this catches the boot window. <<<", flush=True)

    while time.time() < deadline:
        attempt += 1
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(
                HOST, username=USER, password=pw,
                timeout=12, banner_timeout=15, auth_timeout=15,
                look_for_keys=False, allow_agent=False,
            )
        except Exception as ex:  # noqa: BLE001
            remaining = int(deadline - time.time())
            print(f"[{_now()}] attempt {attempt} no session ({type(ex).__name__}); {remaining}s left", flush=True)
            try:
                ssh.close()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(args.interval)
            continue

        try:
            remediate(ssh)
        finally:
            try:
                ssh.close()
            except Exception:  # noqa: BLE001
                pass
        return 0

    print(f"\n[{_now()}] Gave up after {args.minutes:g} min — box never let a session through.")
    print("Reboot again from Vultr console and re-run this script to catch the boot window.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Install logrotate for masternoder.dk, remove bloated uWSGI logs, deploy uwsgi_common.ini fix.

  python scripts/setup_logrotate_remote.py
  python scripts/setup_logrotate_remote.py --purge-logs   # also truncate active uwsgi logs + trim app logs
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deploy_ssh_env import connect_deploy_ssh

REMOTE_BASE = "/var/www/html"
LOGROTATE_DEST = "/etc/logrotate.d/masternoder"
CRON_FILE = "/etc/cron.daily/masternoder-log-cleanup"


def _upload_logrotate(ssh, local: Path) -> None:
    content = local.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    cmd = f"cat > /tmp/masternoder.logrotate <<'LOGROTATE_EOF'\n{content}LOGROTATE_EOF"
    _run(ssh, cmd, timeout=30)


def _upload_file(ssh, local: Path, remote: str) -> None:
    content = local.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    sftp = ssh.open_sftp()
    try:
        with sftp.file(remote, "wb") as f:
            f.write(content)
    finally:
        sftp.close()


def _run(ssh, cmd: str, timeout: int = 120) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    err = (stderr.read() or b"").decode("utf-8", errors="replace")
    if err.strip():
        out += "\n" + err
    return out.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Install logrotate and clean uWSGI logs on server")
    parser.add_argument(
        "--purge-logs",
        action="store_true",
        help="Delete legacy rotated logs, truncate active uwsgi logs, trim old app logs",
    )
    args = parser.parse_args()

    logrotate_local = ROOT / "scripts" / "logrotate" / "masternoder.conf"
    uwsgi_common = ROOT / "uwsgi_common.ini"
    if not logrotate_local.is_file():
        print("Missing", logrotate_local)
        return 1

    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")

    print("=== Disk before ===")
    print(_run(ssh, "df -h / | tail -1"))

    # Deploy uwsgi_common.ini (removes log-maxsize)
    print("\n=== Deploy uwsgi_common.ini (disable uWSGI log-maxsize) ===")
    _upload_file(ssh, uwsgi_common, f"{REMOTE_BASE}/uwsgi_common.ini")
    print("  uploaded")

    # Install logrotate config
    print("\n=== Install logrotate ===")
    _upload_logrotate(ssh, logrotate_local)
    print(_run(ssh, f"install -m 644 /tmp/masternoder.logrotate {LOGROTATE_DEST}"))
    dry = _run(ssh, f"logrotate -d {LOGROTATE_DEST} 2>&1")
    if "error:" in dry.lower():
        print("  [WARN] logrotate dry-run:", dry[-400:])
    else:
        print("  logrotate config OK")

    # Daily safety net: delete any legacy timestamped uwsgi logs + old app log files
    cron_script = r"""#!/bin/sh
# masternoder.dk — prevent log disk fill (legacy uwsgi.log.TIMESTAMP + old app logs)
rm -f /var/www/html/uwsgi.log.[0-9]* /var/www/html/uwsgi_5001.log.[0-9]* 2>/dev/null || true
find /var/www/html/logs -type f \( -name '*.log' -o -name '*.jsonl' \) -mtime +14 -delete 2>/dev/null || true
"""
    sftp = ssh.open_sftp()
    try:
        with sftp.file("/tmp/masternoder-log-cleanup", "w") as f:
            f.write(cron_script)
    finally:
        sftp.close()
    print(_run(ssh, f"install -m 755 /tmp/masternoder-log-cleanup {CRON_FILE}"))

    if args.purge_logs:
        print("\n=== Purge bloated logs ===")
        purge = r"""bash -s <<'EOF'
set +e
echo 'Removing legacy uwsgi rotated files...'
du -ch /var/www/html/uwsgi.log.[0-9]* /var/www/html/uwsgi_5001.log.[0-9]* 2>/dev/null | tail -1
rm -f /var/www/html/uwsgi.log.[0-9]* /var/www/html/uwsgi_5001.log.[0-9]* 2>/dev/null

echo 'Truncating active uwsgi logs...'
for f in /var/www/html/uwsgi.log /var/www/html/uwsgi_5001.log; do
  if [ -f "$f" ]; then
    sz=$(stat -c%s "$f" 2>/dev/null || echo 0)
    truncate -s 0 "$f" 2>/dev/null && echo "  truncated $f (was $(( sz / 1024 / 1024 )) MB)"
  fi
done

echo 'Trimming app logs older than 7 days...'
find /var/www/html/logs -type f -mtime +7 -delete 2>/dev/null || true
du -sh /var/www/html/logs 2>/dev/null

echo 'Running logrotate once...'
logrotate -f /etc/logrotate.d/masternoder 2>&1 || true
EOF"""
        print(_run(ssh, purge, timeout=180))

    print("\n=== Reload uWSGI (pick up uwsgi_common.ini) ===")
    print(_run(ssh, "systemctl restart uwsgi-vidgenerator 2>&1; sleep 3; systemctl is-active uwsgi-vidgenerator"))

    print("\n=== Disk after ===")
    print(_run(ssh, "df -h / | tail -1"))
    print(_run(ssh, "ls -lh /var/www/html/uwsgi.log /var/www/html/uwsgi_5001.log 2>/dev/null; ls /var/www/html/uwsgi.log.[0-9]* 2>/dev/null | wc -l | xargs -I{} echo 'legacy rotated files: {}'"))

    ssh.close()
    print("\nDone. logrotate: daily, max 3 rotations (~30MB) per uwsgi log.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

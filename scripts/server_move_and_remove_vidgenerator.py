#!/usr/bin/env python3
"""
On the production server: move all content from /var/www/html/vidgenerator to /var/www/html,
update uwsgi to use /var/www/html/uwsgi.ini, then delete the old vidgenerator folder contents
(keep only vidgenerator/src for Python imports) and remove .venv to free space.
Run after deploying the new layout (root static/, index.html, uwsgi.ini, page dirs) so server has them.
"""
import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE = "/var/www/html"
VG = f"{REMOTE}/vidgenerator"

# Same page dirs as move_vidgenerator_to_root.py (must match)
PAGE_DIRS = (
    "academic-perspective admin advanced_calculator agent_support agents aggregator "
    "analytics battle battlegrounds beta_testing champions-league chat compendium "
    "danish-divine-tech-tree dashboard debugger editor gallery game generator lab "
    "leaderboards metal milkyway monetization news points profile quests rights-law "
    "shop social starmap25 stats theme_premium theme-points time-achievement-guides "
    "trophies unified_dashboard victory-tech-tree videos"
).split()


def run(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    err = (stderr.read() or b"").decode("utf-8", errors="replace")
    return out.strip(), err.strip()


def main():
    print("=" * 60)
    print("Server: move vidgenerator content to root, then remove old folder")
    print("=" * 60)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    # 1) Merge static: copy VG/static/* to REMOTE/static/
    print("\n[1] Merge vidgenerator/static into /var/www/html/static/")
    run(ssh, f"mkdir -p {REMOTE}/static && for f in {VG}/static/*; do [ -e \"$f\" ] && cp -a \"$f\" {REMOTE}/static/; done 2>/dev/null; echo done", timeout=30)
    # 2) Copy index.html, service-worker.js to root
    print("[2] Copy index.html, service-worker.js to root")
    run(ssh, f"cp -f {VG}/index.html {REMOTE}/ 2>/dev/null; cp -f {VG}/service-worker.js {REMOTE}/ 2>/dev/null; echo done")
    # 3) Copy page dirs to root
    print("[3] Copy page dirs to root")
    for d in PAGE_DIRS:
        run(ssh, f"if [ -d {VG}/{d} ]; then rm -rf {REMOTE}/{d}; cp -a {VG}/{d} {REMOTE}/; fi", timeout=15)
    # 4) Ensure uwsgi.ini at root (deploy should have put it)
    print("[4] Ensure uwsgi.ini at root and update systemd")
    run(ssh, f"test -f {REMOTE}/uwsgi.ini || cp {VG}/uwsgi.ini {REMOTE}/uwsgi.ini 2>/dev/null; sed -i 's|vidgenerator/uwsgi.log|uwsgi.log|' {REMOTE}/uwsgi.ini 2>/dev/null; echo done")
    # Update systemd unit to use root uwsgi.ini
    run(ssh, "sed -i 's|/var/www/html/vidgenerator/uwsgi.ini|/var/www/html/uwsgi.ini|g' /etc/systemd/system/uwsgi-vidgenerator.service 2>/dev/null; systemctl daemon-reload 2>/dev/null; echo done", timeout=10)
    # 5) Remove from vidgenerator everything except src (and delete .venv)
    print("[5] Remove old vidgenerator contents (keep only vidgenerator/src)")
    run(ssh, f"rm -rf {VG}/.venv 2>/dev/null; for x in {VG}/*; do [ -e \"$x\" ] && [ \"$(basename \"$x\")\" != 'src' ] && rm -rf \"$x\"; done; echo done", timeout=30)
    # 6) Permissions
    print("[6] chown www-data")
    run(ssh, f"chown -R www-data:www-data {REMOTE}", timeout=30)
    # 7) Restart uwsgi
    print("[7] Restart uwsgi-vidgenerator")
    run(ssh, "systemctl restart uwsgi-vidgenerator", timeout=120)
    out, _ = run(ssh, "systemctl is-active uwsgi-vidgenerator", timeout=10)
    print(f"  uwsgi-vidgenerator: {out}")
    ssh.close()
    print("\nDone. /var/www/html/vidgenerator now only contains src/. Test: https://masternoder.dk/")


if __name__ == "__main__":
    main()

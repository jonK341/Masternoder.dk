#!/usr/bin/env python3
"""
Install requirements.txt on the production server: create venv, pip install, set uWSGI to use it, restart.
Run from your PC:  python scripts/install_requirements_on_server.py

Requires: requirements.txt and uwsgi.ini deployed at /var/www/html on the server.
Checks disk space before install (torch/transformers need several GB); warns if < MIN_FREE_GB.
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
REMOTE_BASE = "/var/www/html"
REQ_FILE = os.environ.get("INSTALL_REQUIREMENTS_FILE", "requirements.txt")
REMOTE_REQ = f"{REMOTE_BASE}/{os.path.basename(REQ_FILE)}"
VENV_PATH = f"{REMOTE_BASE}/.venv"
UWSGI_INI = f"{REMOTE_BASE}/uwsgi.ini"
MIN_FREE_GB = 2 if "production" in REQ_FILE.lower() else 3  # Slim file needs less space


def run(ssh, cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    try:
        out = (stdout.read() or b"").decode(errors="replace").strip()
    except Exception:
        out = ""
    try:
        err = (stderr.read() or b"").decode(errors="replace").strip()
    except Exception:
        err = ""
    return out, err


def check_disk_space(ssh):
    """Return (avail_gb, message). Parse df -h for / and for mount containing REMOTE_BASE."""
    out, _ = run(ssh, "df -BG / /var 2>/dev/null | tail -n +2")
    lines = (out or "").strip().splitlines()
    msg = []
    min_avail = None
    for line in lines:
        parts = line.split()
        if len(parts) >= 4:
            try:
                avail = int(parts[3].replace("G", ""))
            except ValueError:
                avail = 0
            mount = parts[5] if len(parts) > 5 else parts[0]
            msg.append(f"  {mount}: {parts[3]} available")
            if min_avail is None or avail < min_avail:
                min_avail = avail
    return (min_avail if min_avail is not None else 0, "\n".join(msg) if msg else "  (no df output)")


def main():
    print("=" * 60)
    print("Install requirements on production server")
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    # Check disk space (torch + transformers need several GB)
    print("\n[0] Disk space on server:")
    avail_gb, space_msg = check_disk_space(ssh)
    print(space_msg)
    if avail_gb is not None and avail_gb < MIN_FREE_GB:
        print(f"\n  [WARN] Only ~{avail_gb} GB free (recommend >= {MIN_FREE_GB} GB for full requirements.txt).")
        print("  Consider: free space, or use a slimmer requirements-production.txt (e.g. without torch/transformers).")
        if os.environ.get("INSTALL_REQUIREMENTS_YES") != "1":
            reply = input("  Continue anyway? [y/N]: ").strip().lower()
            if reply != "y":
                print("  Aborted.")
                ssh.close()
                sys.exit(1)
        else:
            print("  Continuing (--yes).")

    sftp = ssh.open_sftp()
    local_req = PROJECT_ROOT / REQ_FILE
    if local_req.exists():
        sftp.put(str(local_req), REMOTE_REQ)
        print(f"[0] Uploaded {REQ_FILE} -> {REMOTE_REQ}")
    sftp.close()

    # Ensure pdb++ is pdbpp on server (only for full requirements.txt)
    if "production" not in REQ_FILE.lower():
        run(ssh, f"sed -i 's/^pdb++/pdbpp/' {REMOTE_REQ} 2>/dev/null; true")

    # Create venv if missing
    print("\n[1] Create venv if missing...")
    out, err = run(ssh, f"test -d {VENV_PATH} && echo exists || (python3 -m venv {VENV_PATH} && echo created)", timeout=60)
    print(f"  {out or err or 'done'}")

    # Upgrade pip and install requirements (torch/transformers can take 10+ min and 2–4 GB)
    print("\n[2] Install requirements (this may take 10–20 min; torch is large)...")
    pip_cmd = f"{VENV_PATH}/bin/pip install --upgrade pip && {VENV_PATH}/bin/pip install -r {REMOTE_REQ}; e=$?; echo PIP_EXIT=$e"
    out, err = run(ssh, pip_cmd, timeout=1200)
    pip_ok = "PIP_EXIT=0" in (out or "") or "Successfully installed" in (out or "")
    try:
        if err and "ERROR" in err and "Successfully" not in (out or ""):
            print("  stderr:", (err[:500]).encode("ascii", errors="replace").decode())
        if out:
            for line in out.splitlines()[-15:]:
                print(" ", line.encode("ascii", errors="replace").decode())
    except (UnicodeEncodeError, UnicodeDecodeError):
        print("  (pip output omitted)")
    if pip_ok:
        print("  [OK] pip install finished")
    else:
        print("  [WARN] pip may have failed (e.g. no space left). Check server: df -h; tail -50 /var/www/html/.venv/pip.log 2>/dev/null")
        print("  If out of space: free some disk or use a slimmer requirements-production.txt (e.g. omit torch/transformers).")

    # chown venv to www-data so uWSGI can use it
    print("\n[3] chown venv to www-data...")
    run(ssh, f"chown -R www-data:www-data {VENV_PATH}")
    print("  [OK]")

    # Point uwsgi.ini at venv (uncomment and set path)
    print("\n[4] Configure uwsgi to use venv...")
    run(ssh, f"sed -i 's|^# virtualenv = .*|virtualenv = {VENV_PATH}|' {UWSGI_INI}; sed -i 's|^virtualenv = .*|virtualenv = {VENV_PATH}|' {UWSGI_INI}")
    out, _ = run(ssh, f"grep -E '^virtualenv|^# virtualenv' {UWSGI_INI} | head -1")
    print(f"  {out.strip() or ('virtualenv = ' + VENV_PATH)}")
    print("  [OK]")

    # Restart uWSGI
    print("\n[5] Restart uwsgi-vidgenerator...")
    run(ssh, "systemctl restart uwsgi-vidgenerator", timeout=30)
    out, _ = run(ssh, "systemctl is-active uwsgi-vidgenerator")
    print(f"  Status: {out.strip() or 'unknown'}")

    # Show disk space after install
    print("\n[6] Disk space after install:")
    _, space_after = check_disk_space(ssh)
    print(space_after)

    ssh.close()
    print("\n" + "=" * 60)
    print("Done. Workers may take 90–150s to load. Test: https://masternoder.dk/")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Install requirements on production server (with disk space check)")
    ap.add_argument("-y", "--yes", action="store_true", help="Skip 'continue anyway?' when space is low")
    ap.add_argument("-p", "--production", action="store_true", help="Use requirements-production.txt (slim, no torch/opencv)")
    args = ap.parse_args()
    if args.yes:
        os.environ["INSTALL_REQUIREMENTS_YES"] = "1"
    if args.production:
        os.environ["INSTALL_REQUIREMENTS_FILE"] = "requirements-production.txt"
    main()

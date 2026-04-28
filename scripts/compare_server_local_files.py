#!/usr/bin/env python3
"""
Compare Local vs Server Files - Ubuntu production vs local.
Shows: exists, size, modification date. Lists files missing on server.
"""
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"

# Critical files to compare (deploy list + register_intelligence + key backend)
FILES_TO_COMPARE = [
    "src/app/__init__.py",
    "backend/route_loader.py",
    "backend/register_blueprints.py",
    "backend/routes/missing_endpoints_routes.py",
    "backend/routes/battle_routes.py",
    "backend/middleware/auto_fix_404_middleware.py",
    "wsgi.py",
    "vidgenerator/wsgi.py",
    "vidgenerator/generator/index.html",
    "vidgenerator/lab/index.html",
    "vidgenerator/service-worker.js",
    "vidgenerator/static/js/unified-generator-battle.js",
    "vidgenerator/static/js/trigger-based-actions.js",
    "vidgenerator/static/js/navigation-toolbar.js",
    "backend/services/video_generator_service.py",
    "backend/services/generator_context_service.py",
    "backend/services/auto_fix_endpoints.py",
    "data/content_categories.json",
]
# Add register_intelligence package
for name in ["__init__.py", "route_discovery.py", "frontend_api_scanner.py", "orchestrator.py", "missing_route_resolver.py"]:
    FILES_TO_COMPARE.append(f"backend/services/register_intelligence/{name}")


def fmt_ts(ts):
    if ts is None:
        return "N/A"
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)


def run():
    print("=" * 75)
    print("LOCAL vs SERVER FILE COMPARISON")
    print("=" * 75)
    print("Server:", SERVER_HOST, "| Remote base:", REMOTE_BASE)
    print("Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()

    try:
        import paramiko
    except ImportError:
        print("[ERROR] Install paramiko: pip install paramiko")
        return False

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    except Exception as e:
        print(f"[ERROR] Cannot connect: {e}")
        return False

    sftp = ssh.open_sftp()
    os.chdir(BASE_DIR)

    missing_on_server = []
    missing_locally = []
    diff_size = []
    diff_date = []

    print(f"{'File':<50} {'Local Size':<10} {'Server':<10} {'Local Date':<16} {'Server Date':<16} {'Status'}")
    print("-" * 120)

    for rel in FILES_TO_COMPARE:
        local_path = os.path.join(BASE_DIR, rel.replace("/", os.sep))
        remote_path = f"{REMOTE_BASE}/{rel.replace(os.sep, '/')}"

        local_exists = os.path.exists(local_path)
        try:
            remote_stat = sftp.stat(remote_path)
            remote_exists = True
            remote_size = remote_stat.st_size
            remote_mtime = remote_stat.st_mtime
        except (FileNotFoundError, IOError):
            remote_exists = False
            remote_size = None
            remote_mtime = None

        if not local_exists:
            missing_locally.append(rel)
            status = "MISSING LOCAL"
        elif not remote_exists:
            missing_on_server.append(rel)
            local_size = os.path.getsize(local_path)
            status = "MISSING ON SERVER"
        else:
            local_size = os.path.getsize(local_path)
            if local_size != remote_size:
                diff_size.append((rel, local_size, remote_size))
                status = f"SIZE DIFF ({local_size} vs {remote_size})"
            else:
                status = "OK"

        loc_s = str(local_size) if local_exists else "N/A"
        rem_s = str(remote_size) if remote_exists else "N/A"
        loc_date = fmt_ts(os.path.getmtime(local_path)) if local_exists and os.path.exists(local_path) else "N/A"
        rem_date = fmt_ts(remote_mtime) if remote_mtime else "N/A"
        print(f"{rel[:49]:<50} {loc_s:<10} {rem_s:<10} {loc_date:<16} {rem_date:<16} {status}")

    sftp.close()
    ssh.close()

    print()
    print("=" * 75)
    print("SUMMARY")
    print("=" * 75)
    print(f"Total compared: {len(FILES_TO_COMPARE)}")
    print(f"Missing on server: {len(missing_on_server)}")
    print(f"Missing locally: {len(missing_locally)}")
    print(f"Size differences: {len(diff_size)}")

    if missing_on_server:
        print()
        print("FILES MISSING ON SERVER (deploy these):")
        for f in missing_on_server:
            print("  -", f)

    if missing_locally:
        print()
        print("FILES MISSING LOCALLY:")
        for f in missing_locally:
            print("  -", f)

    if diff_size:
        print()
        print("SIZE DIFFERENCES (content may differ):")
        for rel, ls, rs in diff_size[:15]:
            print(f"  {rel}: local={ls} server={rs}")

    print()
    return True


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)

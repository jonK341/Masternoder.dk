#!/usr/bin/env python3
"""
Deploy only index files and key page/static assets (lightweight deploy).
Uploads: root index.html, service-worker.js, uwsgi.ini; each page's index.html;
optional backend route and main CSS/JS. Use when you only changed content, not the full app.

Usage:
  python scripts/deploy_index_and_pages.py              # Upload index + pages, restart uwsgi
  python scripts/deploy_index_and_pages.py --dry-run    # List files only
  python scripts/deploy_index_and_pages.py --no-restart # Upload without restart
"""
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

# Remote
SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"

# Root-level single files
ROOT_FILES = [
    "index.html",
    "service-worker.js",
    "uwsgi.ini",
    "requirements-production.txt",
]

# Page dirs: we upload only index.html from each (and optional other HTML in that dir)
PAGE_DIRS = [
    "generator", "gallery", "shop", "battle", "chat", "debugger", "leaderboards", "quests",
    "news", "metal", "theme-points", "battlegrounds", "champions-league", "editor", "monetization",
    "milkyway", "rights-law", "victory-tech-tree", "danish-divine-tech-tree", "academic-perspective",
    "theme_premium", "time-achievement-guides", "beta_testing", "unified_dashboard", "advanced_calculator",
    "agent_support", "game", "lab", "stats", "social", "profile", "aggregator", "points", "trophies",
    "dashboard", "analytics", "compendium", "starmap25", "agents", "admin",
]

# Optional: one route file and main static assets (so 500 fix / styling go up without full deploy)
EXTRA_FILES = [
    "backend/routes/all_page_routes.py",
    "static/css/modern-design-system.css",
    "static/js/navigation-toolbar.js",
    "static/js/service-worker-gatherer.js",
]


def collect_files():
    """Collect relative paths: root files, each page's index.html, extras."""
    out = []
    for name in ROOT_FILES:
        if (PROJECT_ROOT / name).is_file():
            out.append(name)
    for dir_name in PAGE_DIRS:
        index_path = PROJECT_ROOT / dir_name / "index.html"
        if index_path.is_file():
            out.append(f"{dir_name}/index.html")
        # Nested: dashboard/master_control
        if dir_name == "dashboard":
            nested = PROJECT_ROOT / "dashboard" / "master_control" / "index.html"
            if nested.is_file():
                out.append("dashboard/master_control/index.html")
    for rel in EXTRA_FILES:
        if (PROJECT_ROOT / rel).is_file():
            out.append(rel)
    return sorted(out)


def main():
    try:
        import paramiko
    except ImportError:
        print("pip install paramiko")
        sys.exit(1)

    import argparse
    ap = argparse.ArgumentParser(description="Deploy only index files and key pages")
    ap.add_argument("--dry-run", action="store_true", help="List files only, no upload")
    ap.add_argument("--no-restart", action="store_true", help="Do not restart uwsgi after upload")
    args = ap.parse_args()

    files = collect_files()
    print("=" * 55)
    print("Deploy index + pages (lightweight)")
    print("=" * 55)
    print(f"Files to upload: {len(files)}")
    for f in files[:25]:
        print(f"  {f}")
    if len(files) > 25:
        print(f"  ... and {len(files) - 25} more")
    print()

    if args.dry_run:
        print("[DRY-RUN] No upload.")
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    sftp = ssh.open_sftp()

    uploaded = 0
    for local_rel in files:
        local_path = PROJECT_ROOT / local_rel
        if not local_path.is_file():
            print(f"  [SKIP] {local_rel} (missing)")
            continue
        remote = f"{REMOTE_BASE}/{local_rel}"
        remote_dir = os.path.dirname(remote)
        try:
            ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=5)
        except Exception:
            pass
        try:
            with open(local_path, "rb") as f:
                content = f.read()
            with sftp.file(remote, "wb") as rf:
                rf.write(content)
            uploaded += 1
        except Exception as e:
            print(f"  [ERROR] {local_rel}: {e}")
    sftp.close()

    print(f"  Uploaded: {uploaded} files")

    if not args.no_restart and uploaded:
        print("  Restarting uwsgi-vidgenerator...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator", timeout=90)
        stdout.read()
        stderr.read()
        print("  Done. Test: https://masternoder.dk/")
    ssh.close()
    print("=" * 55)


if __name__ == "__main__":
    main()

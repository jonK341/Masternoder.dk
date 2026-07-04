#!/usr/bin/env python3
"""
Deploy all files to server and restart uwsgi-vidgenerator on port 5000.
Single service (no emperor). See docs/DEPLOYMENT_PLAN.md.

Usage:
  python scripts/deploy_all_and_restart_uwsgi.py [--dry-run] [--no-upload]
  python scripts/deploy_all_and_restart_uwsgi.py --manifest profile loading  # deploy only those manifests then restart
  python scripts/deploy_all_and_restart_uwsgi.py --no-upload                 # restart uwsgi-vidgenerator only (e.g. after config change)

After deploy: run python scripts/test_url_timing.py (with BASE_URL to production) to verify. See docs/CHECKPOINTS_RECHECK.md.
SSH: tries DEPLOY_KEY_PATH / ~/.ssh keys first, then DEPLOY_PASS (.env or --ask-pass).
Server: masternoder.dk, REMOTE_BASE /var/www/html.
"""
import os
import sys
import subprocess
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko")
    sys.exit(1)

from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user, require_deploy_pass

SERVER_HOST = deploy_host()
SERVER_USER = deploy_user()
REMOTE_BASE = "/var/www/html"


def _exec(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode().strip()
    err = (stderr.read() or b"").decode().strip()
    return out, err


# Root-level page dirs and files (moved from vidgenerator/ for space; uwsgi.ini at root)
ROOT_PAGE_DIRS = (
    "static", "generator", "gallery", "shop", "battle", "chat", "debugger", "leaderboards", "quests",
    "news", "metal", "theme-points", "battlegrounds", "champions-league", "editor", "monetization",
    "milkyway", "rights-law", "victory-tech-tree", "danish-divine-tech-tree", "academic-perspective",
    "theme_premium", "time-achievement-guides", "beta_testing", "unified_dashboard", "advanced_calculator",
    "agent_support", "game", "lab", "stats", "social", "profile", "aggregator", "points", "trophies",
    "dashboard", "analytics", "compendium", "starmap25", "agents", "admin", "videos",
)
ROOT_FILES = ("index.html", "service-worker.js", "uwsgi.ini", ".env")


def collect_all_files(root: Path, exclude_dirs: tuple = (".git", ".venv", "__pycache__", "node_modules")) -> list:
    """Collect all files under vidgenerator, backend, scripts, docs, data, plus root layout (static, pages, uwsgi.ini)."""
    rels = []
    for top in ("vidgenerator", "backend", "scripts", "docs", "data", "systemd", "config"):
        d = root / top
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if p.is_file():
                skip = False
                for part in p.relative_to(root).parts:
                    if part in exclude_dirs or part.endswith(".pyc"):
                        skip = True
                        break
                if skip:
                    continue
                rels.append(str(p.relative_to(root)).replace(os.sep, "/"))
    for f in ROOT_FILES:
        if (root / f).is_file():
            rels.append(f)
    for top in ROOT_PAGE_DIRS:
        d = root / top
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.is_file():
                skip = any(part in exclude_dirs for part in p.relative_to(root).parts)
                if not skip:
                    rels.append(str(p.relative_to(root)).replace(os.sep, "/"))
    return sorted(rels)


def get_manifest_files(root: Path, manifest_names: list) -> list:
    """Get file list from deploy.py MANIFESTS by name."""
    import importlib.util
    deploy_py = root / "scripts" / "deploy.py"
    MANIFESTS = {}
    if deploy_py.exists():
        try:
            spec = importlib.util.spec_from_file_location("deploy", deploy_py)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            MANIFESTS = getattr(mod, "MANIFESTS", {})
        except Exception:
            pass
    files = []
    for name in manifest_names:
        name = name.lower()
        if name in MANIFESTS:
            files.extend(MANIFESTS[name])
    return list(dict.fromkeys(files))  # unique, keep order


def run(
    files: list,
    dry_run: bool = False,
    no_upload: bool = False,
    skip_gunicorn_check: bool = False,
    server_pass: Optional[str] = None,
):
    ssh = None
    sftp = None

    try:
        print("=" * 60)
        print("DEPLOY ALL & RESTART UWSGI (port 5000)")
        print("=" * 60)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print()

        os.chdir(PROJECT_ROOT)

        print("[1] Connecting...")
        sys.stdout.flush()
        ssh, auth_method, _ = connect_deploy_ssh(server_pass)
        if no_upload:
            print("  [SKIP] Upload disabled (--no-upload)")
        else:
            sftp = ssh.open_sftp()
        print(f"  [OK] Connected ({auth_method})")
        print()
        sys.stdout.flush()

        # --- Kill gunicorn and free port 5000 FIRST (fix 502: nginx needs uwsgi on 5000, not gunicorn) ---
        if not dry_run and not skip_gunicorn_check:
            print("[2] Killing gunicorn and freeing port 5000 first...")
            sys.stdout.flush()
            _exec(ssh, "systemctl stop vidgenerator-gunicorn 2>/dev/null || true", timeout=10)
            _exec(ssh, "pkill -f gunicorn 2>/dev/null || true", timeout=5)
            time.sleep(1)
            out, _ = _exec(ssh, "ss -tlnp 2>/dev/null | grep ':5000 ' || true", timeout=5)
            if out.strip():
                which_out, _ = _exec(ssh, "which fuser 2>/dev/null || true", timeout=3)
                if which_out.strip():
                    _exec(ssh, "fuser -k 5000/tcp 2>/dev/null || true", timeout=5)
                else:
                    _exec(ssh, "for p in $(ss -tlnp 2>/dev/null | grep ':5000 ' | sed -n 's/.*pid=\\([0-9]*\\).*/\\1/p'); do kill $p 2>/dev/null; done", timeout=5)
                time.sleep(1)
            print("  [OK] Port 5000 cleared (gunicorn killed)")
        else:
            print("[2] (dry-run or skip) Would kill gunicorn and free port 5000 first")
        print()
        sys.stdout.flush()

        # --- Stop uwsgi (run in background on server to avoid SSH read timeout) ---
        print("[3] Stopping uwsgi...")
        sys.stdout.flush()
        try:
            ssh.exec_command("(systemctl stop uwsgi 2>/dev/null; systemctl stop uwsgi-vidgenerator 2>/dev/null; pkill -f uwsgi 2>/dev/null; true) &", timeout=5)
        except Exception:
            pass
        time.sleep(3)
        print("  [OK] uwsgi stopped")
        print()
        sys.stdout.flush()

        if not no_upload and files:
            print("[4] Uploading files...")
            sys.stdout.flush()
            deployed = 0
            for local in files:
                if not (PROJECT_ROOT / local).exists():
                    print(f"  [SKIP] {local} (missing)")
                    continue
                remote = f"{REMOTE_BASE}/{local}"
                remote_dir = os.path.dirname(remote)
                if dry_run:
                    print(f"  [DRY] {local} -> {remote}")
                    deployed += 1
                    continue
                try:
                    ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=5)
                    time.sleep(0.05)
                except Exception:
                    pass
                try:
                    with open(PROJECT_ROOT / local, "rb") as f:
                        content = f.read()
                    with sftp.file(remote, "wb") as rf:
                        rf.write(content)
                    deployed += 1
                    if deployed % 50 == 0:
                        print(f"  ... {deployed} files")
                        sys.stdout.flush()
                except Exception as e:
                    print(f"  [ERROR] {local}: {e}")
            if sftp:
                sftp.close()
            print(f"  [SUMMARY] {deployed} files uploaded")
            sys.stdout.flush()
        else:
            print("[4] Skipping upload (no files or --no-upload)")
        print()

        if not dry_run:
            print("[5] Clearing cache...")
            _exec(ssh, f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true", timeout=30)
            _exec(ssh, f"find {REMOTE_BASE} -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
            _exec(ssh, "rm -rf /var/cache/nginx/* 2>/dev/null || true", timeout=10)
            print("  [OK] Cache cleared")
            print()

        # --- Ensure port 5000 is still free before starting uwsgi ---
        if not dry_run and not skip_gunicorn_check:
            out, _ = _exec(ssh, "ss -tlnp 2>/dev/null | grep ':5000 ' || true", timeout=5)
            if out.strip():
                print("[5b] Port 5000 in use again; freeing...")
                which_out, _ = _exec(ssh, "which fuser 2>/dev/null || true", timeout=3)
                if which_out.strip():
                    _exec(ssh, "fuser -k 5000/tcp 2>/dev/null || true", timeout=5)
                else:
                    _exec(ssh, "for p in $(ss -tlnp 2>/dev/null | grep ':5000 ' | sed -n 's/.*pid=\\([0-9]*\\).*/\\1/p'); do kill $p 2>/dev/null; done", timeout=5)
                time.sleep(1)
                print("  [OK] Port 5000 cleared")
            print()

        if dry_run:
            print("[6] Dry-run: would start uwsgi and reload nginx")
            ssh.close()
            return True

        # --- If we deployed systemd units, copy to /etc/systemd/system/ and daemon-reload (so EnvironmentFile=.env is used) ---
        if not no_upload and any("systemd/" in f for f in files):
            print("[5c] Installing systemd units (so .env / MN2_RPC_* are loaded)...")
            for unit in ("uwsgi-vidgenerator.service", "uwsgi-vidgenerator-5001.service"):
                _exec(ssh, f"cp {REMOTE_BASE}/systemd/{unit} /etc/systemd/system/ 2>/dev/null && echo OK || true", timeout=5)
            _exec(ssh, "systemctl daemon-reload", timeout=10)
            print("  [OK] systemd units installed and daemon-reloaded")

        # --- Start uwsgi-vidgenerator (single service; never use emperor for this app) ---
        print("[6] Starting uwsgi-vidgenerator...")
        _exec(ssh, "systemctl start uwsgi-vidgenerator", timeout=15)
        time.sleep(3)
        out, _ = _exec(ssh, "systemctl is-active uwsgi-vidgenerator 2>/dev/null || echo inactive", timeout=5)
        if "active" in out:
            print("  [OK] uwsgi-vidgenerator active")
        else:
            print("  [WARN] uwsgi-vidgenerator status:", out.strip() or "unknown")
        print()

        # --- Verify :5000 ---
        print("[7] Verifying :5000...")
        for attempt in range(8):
            time.sleep(2)
            try:
                out, _ = _exec(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/ 2>/dev/null || echo 000", timeout=15)
            except Exception as e:
                if attempt < 7:
                    continue
                print("  [WARN] Verify timeout (uwsgi may still be starting):", str(e)[:50])
                break
            if out and out != "000":
                try:
                    c = int(out)
                    if 200 <= c < 600 or c in (301, 302):
                        print("  [OK] Upstream :5000 responding HTTP", c)
                        break
                except ValueError:
                    pass
        else:
            print("  [WARN] Upstream :5000 not ready (or check timed out)")
        _exec(ssh, "nginx -t 2>&1 || true", timeout=10)
        _exec(ssh, "systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", timeout=15)
        print("  [OK] Nginx reloaded")
        # Ensure nginx proxy + 300s timeouts (avoid 502/504 on slow requests)
        nginx_fix = PROJECT_ROOT / "scripts" / "fix_502_nginx_only.py"
        if nginx_fix.exists():
            print("  [6b] Applying nginx proxy + timeouts (300s)...")
            try:
                subprocess.run(
                    [sys.executable, str(nginx_fix)],
                    cwd=PROJECT_ROOT,
                    timeout=90,
                    capture_output=True,
                )
            except Exception:
                pass
        print()
        print("=" * 60)
        print("DEPLOY & UWSGI RESTART COMPLETE")
        print("=" * 60)
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass
        return False


def main():
    ap = argparse.ArgumentParser(description="Deploy all files and restart uwsgi-vidgenerator on port 5000; single service (see docs/DEPLOYMENT_PLAN.md)")
    ap.add_argument("--dry-run", action="store_true", help="Do not upload or restart; show planned steps")
    ap.add_argument("--no-upload", action="store_true", help="Do not upload files; only restart uwsgi-vidgenerator (still stop, clear port, start)")
    ap.add_argument("--skip-gunicorn-check", action="store_true", help="Do not kill gunicorn / free port 5000 (not recommended)")
    ap.add_argument("--manifest", nargs="+", metavar="NAME", help="Deploy only these manifest names from deploy.py (e.g. profile loading); default: all files")
    ap.add_argument("--ask-pass", action="store_true", help="Prompt for SSH password (ignores DEPLOY_PASS in .env)")
    args = ap.parse_args()

    server_pass = require_deploy_pass(force_prompt=args.ask_pass)

    if args.manifest:
        files = get_manifest_files(PROJECT_ROOT, args.manifest)
        print(f"Using manifest(s) {args.manifest}: {len(files)} files")
    else:
        files = collect_all_files(PROJECT_ROOT)
        print(f"Deploying all files: {len(files)} files")

    ok = run(
        files,
        dry_run=args.dry_run,
        no_upload=args.no_upload,
        skip_gunicorn_check=args.skip_gunicorn_check,
        server_pass=server_pass,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

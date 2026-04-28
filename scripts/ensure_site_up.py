#!/usr/bin/env python3
"""
Single command to get the site running (90% uptime plan).

Run from your PC when the site is down, 502, or "nothing works":
  python scripts/ensure_site_up.py

Does:
  1. fix_502.py (free port, perms, install/start uwsgi-vidgenerator, test)
  2. fix_502_nginx_only.py (proxy to :5000, 300s timeouts, reload nginx)
  3. Optional: quick HTTPS check

See docs/DEPLOYMENT_PLAN.md.
"""
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent


def main():
    print("=" * 60)
    print("ENSURE SITE UP (fix_502 + nginx timeouts)")
    print("=" * 60)
    os.chdir(PROJECT_ROOT)

    # 1. Full fix (port, perms, uwsgi-vidgenerator). Workers need 60–90s to load; allow up to 5 min.
    print("\n[1] Running fix_502.py ...\n")
    r1 = subprocess.run([sys.executable, "fix_502.py"], cwd=PROJECT_ROOT, timeout=300)
    if r1.returncode != 0:
        print("\n[WARN] fix_502.py exited with", r1.returncode, "- continuing with nginx fix.")

    # 2. Nginx proxy + timeouts so HTTPS works and slow requests don't 504
    print("\n[2] Running fix_502_nginx_only.py ...\n")
    r2 = subprocess.run(
        [sys.executable, "scripts/fix_502_nginx_only.py"],
        cwd=PROJECT_ROOT,
        timeout=120,
    )
    if r2.returncode != 0:
        print("\n[WARN] fix_502_nginx_only.py exited with", r2.returncode)

    print("\n" + "=" * 60)
    print("DONE. Test: https://masternoder.dk/ and https://masternoder.dk/generator (primary); /vidgenerator/ redirects to /")
    print("If still 502: python scripts/investigate_502.py")
    print("=" * 60)
    sys.exit(0 if (r1.returncode == 0 and r2.returncode == 0) else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
When you still get 502 but the app on port 5000 works (e.g. after fix_502.py).
Run from your PC:  python scripts/fix_502_nginx_only.py

Applies: fix_nginx_proxy_all_pages.py + fix_504_timeouts.py (300s) then reloads nginx.
Use when uWSGI is already running and HTTPS returns 502 or "upstream timed out".
"""
import os
import subprocess
import sys

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 1) Ensure all locations proxy to 5000
    for name in ["scripts/fix_nginx_proxy_all_pages.py"]:
        path = os.path.join(root, name)
        if os.path.isfile(path):
            print(f"Running {name}...")
            subprocess.run([sys.executable, path], cwd=root, timeout=90)
    # 2) Set proxy timeouts to 300s so slow/first requests don't hit "upstream timed out"
    path = os.path.join(root, "scripts/fix_504_timeouts.py")
    if os.path.isfile(path):
        print("Running scripts/fix_504_timeouts.py --increase 300...")
        r = subprocess.run(
            [sys.executable, path, "--increase", "300"],
            cwd=root,
            timeout=90,
        )
        if r.returncode != 0:
            print(f"[WARN] fix_504_timeouts.py exited with {r.returncode}")
    # 3) Stable screen: serve 502.html on 502/503/504 so users always see a loading page
    path_502 = os.path.join(root, "scripts/fix_nginx_502_page.py")
    if os.path.isfile(path_502):
        print("Running scripts/fix_nginx_502_page.py (stable loading page)...")
        subprocess.run([sys.executable, path_502], cwd=root, timeout=60)
    print("Done. Test: https://masternoder.dk/ and https://masternoder.dk/generator")

if __name__ == "__main__":
    main()

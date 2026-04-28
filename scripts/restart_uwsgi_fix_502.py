#!/usr/bin/env python3
"""
Full restart uWSGI and verify: stop, free port 5000, start, wait for workers, test.
Use when curl on server returns 502 (Nginx gets no valid response from uWSGI).

Run from your PC:  python scripts/restart_uwsgi_fix_502.py
"""
import os
import sys
import time

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE = "/var/www/html"
WAIT_AFTER_START = 150  # seconds for workers to load 126 blueprints (with swap, first load can be slow)
CURL_TIMEOUT = 90

def run(ssh, cmd, timeout=30):
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

def main():
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    print("=" * 60)
    print("RESTART UWSGI & FIX 502 (clean bind on port 5000)")
    print("=" * 60)

    # 1. Stop uWSGI and free port 5000
    print("\n[1] Stopping uWSGI and freeing port 5000...")
    run(ssh, "systemctl stop uwsgi-vidgenerator 2>/dev/null; systemctl stop uwsgi 2>/dev/null; sleep 2; pkill -9 -f uwsgi 2>/dev/null; sleep 2; fuser -k 5000/tcp 2>/dev/null; sleep 1; echo done", timeout=20)
    out, _ = run(ssh, "ss -tlnp 2>/dev/null | grep ':5000 ' || true")
    if out.strip():
        print("  Port 5000 still in use; forcing...")
        run(ssh, "fuser -k 5000/tcp 2>/dev/null; sleep 2")
    print("  [OK] Port 5000 free")

    # 2. Start uwsgi-vidgenerator
    print("\n[2] Starting uwsgi-vidgenerator...")
    run(ssh, "systemctl start uwsgi-vidgenerator", timeout=15)
    out, _ = run(ssh, "systemctl is-active uwsgi-vidgenerator")
    print(f"  Service: {out.strip() or 'unknown'}")

    # 3. Wait for workers to load (126 blueprints = 60–90s)
    print(f"\n[3] Waiting {WAIT_AFTER_START}s for workers to load...")
    for i in range(WAIT_AFTER_START, 0, -10):
        print(f"  ... {i}s")
        time.sleep(min(10, i))
    print("  [OK] Wait done")

    # 3b. Check if workers finished loading (uwsgi.log)
    log_check, _ = run(ssh, f"grep -E 'SUMMARY|Registered 126|Killed|died' {REMOTE}/uwsgi.log 2>/dev/null | tail -5")
    if log_check and "SUMMARY" in log_check:
        print("  uwsgi.log: blueprints loaded")
    elif log_check and ("Killed" in log_check or "died" in log_check):
        print("  uwsgi.log: worker killed/died – check OOM: dmesg | tail -20")

    # 4. Test direct to uWSGI (this is what Nginx proxies to)
    print(f"\n[4] Testing http://127.0.0.1:5000/ (timeout={CURL_TIMEOUT}s)...")
    code_out, _ = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' --max-time {CURL_TIMEOUT} http://127.0.0.1:5000/ 2>/dev/null || echo '000'", timeout=CURL_TIMEOUT + 10)
    code = (code_out or "").strip()
    if code == "200":
        print(f"  Port 5000: HTTP {code} OK")
    else:
        print(f"  Port 5000: HTTP {code or '000'} (failure or timeout)")
        print("\n  If 000 or timeout: workers may still be loading or crashing. Check:")
        print(f"    tail -80 {REMOTE}/uwsgi.log")
        print(f"    grep -E 'Traceback|Error|died|killed|recursion' {REMOTE}/uwsgi.log")

    # 5. Test via Nginx (HTTPS)
    print(f"\n[5] Testing https://masternoder.dk/ (timeout=30s)...")
    https_out, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' --max-time 30 https://masternoder.dk/ 2>/dev/null || echo '000'", timeout=35)
    https_code = (https_out or "").strip()
    if https_code == "200":
        print(f"  HTTPS: HTTP {https_code} OK")
    else:
        print(f"  HTTPS: HTTP {https_code or '000'} (502 = Nginx could not get response from port 5000)")

    ssh.close()
    print("\n" + "=" * 60)
    if code != "200":
        print("Direct port 5000 still not 200. On the server run:")
        print("  sudo systemctl stop uwsgi-vidgenerator")
        print("  sudo -u www-data /usr/bin/uwsgi --ini /var/www/html/uwsgi.ini")
        print("Then in another terminal: curl -v http://127.0.0.1:5000/")
        print("Look for Python traceback in the first terminal.")
    print("=" * 60)

if __name__ == "__main__":
    main()

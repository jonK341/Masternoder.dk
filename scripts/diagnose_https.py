#!/usr/bin/env python3
"""
Diagnose why HTTPS does not return 200 or the page does not show.
Run from your PC:  python scripts/diagnose_https.py

Checks: app on port 5000, then HTTPS (nginx) for / and /generator (primary).
/vidgenerator/ redirects to /. Shows nginx config so you can fix proxy.
"""
import os
import sys

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
NGINX_CONFIG = "/etc/nginx/sites-enabled/masternoder.dk"


def main():
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)

    print("=" * 60)
    print("HTTPS diagnostic: why no 200 / screen?")
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    def run(cmd, timeout=25):
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
        return out, err

    # 1) App on port 5000 (bypass nginx)
    print("\n[1] App on port 5000 (direct)")
    code_root, _ = run(
        "curl -s -o /dev/null -w '%{http_code}' --max-time 60 http://127.0.0.1:5000/ 2>/dev/null || echo '000'",
        timeout=65,
    )
    code_gen, _ = run(
        "curl -s -o /dev/null -w '%{http_code}' --max-time 60 http://127.0.0.1:5000/generator 2>/dev/null || echo '000'",
        timeout=65,
    )
    print(f"  GET http://127.0.0.1:5000/         -> {code_root or '000'}")
    print(f"  GET http://127.0.0.1:5000/generator -> {code_gen or '000'}")

    # 2) HTTPS via nginx (what the browser sees)
    print("\n[2] HTTPS via nginx (what you see in browser)")
    code_https_root, _ = run(
        "curl -s -o /dev/null -w '%{http_code}' --max-time 30 -k https://127.0.0.1/ -H 'Host: masternoder.dk' 2>/dev/null || echo '000'",
        timeout=35,
    )
    code_https_gen, _ = run(
        "curl -s -o /dev/null -w '%{http_code}' --max-time 30 -k https://127.0.0.1/generator -H 'Host: masternoder.dk' 2>/dev/null || echo '000'",
        timeout=35,
    )
    print(f"  GET https://masternoder.dk/          -> {code_https_root or '000'}")
    print(f"  GET https://masternoder.dk/generator -> {code_https_gen or '000'}")

    # 2b) Second backend (many nginx location blocks use 5001 for /api, /static, etc.)
    print("\n[2b] Second app on port 5001 (if nginx uses 5001 and it is down → blank UI / failed APIs)")
    code_5001, _ = run(
        "curl -s -o /dev/null -w '%{http_code}' --max-time 20 http://127.0.0.1:5001/api/health 2>/dev/null || echo '000'",
        timeout=25,
    )
    print(f"  GET http://127.0.0.1:5001/api/health -> {code_5001 or '000'}")
    nginx_5001_lines, _ = run("grep -n '5001' " + NGINX_CONFIG + " 2>/dev/null | head -30")
    if nginx_5001_lines:
        print("  nginx lines mentioning 5001:")
        for line in nginx_5001_lines.split("\n"):
            print("  ", line)
    else:
        print("  (no 5001 in nginx config snippet)")

    # 3) Nginx config: server and location blocks
    print("\n[3] Nginx config (server_name + location for / and /generator)")
    out, _ = run(f"grep -n 'server_name\\|listen\\|location\\|proxy_pass\\|root\\|alias\\|try_files' {NGINX_CONFIG} 2>/dev/null | head -80")
    if out:
        for line in out.split("\n"):
            print("  ", line)
    else:
        print("  (could not read config)")

    # 4) Nginx error log (502 / upstream errors)
    print("\n[4] Nginx error log (last 15 lines)")
    out, _ = run("tail -15 /var/log/nginx/error.log 2>/dev/null")
    if out:
        for line in out.split("\n"):
            print("  ", line)
    else:
        print("  (empty)")

    ssh.close()

    # Summary
    print("\n" + "=" * 60)
    if (code_root or "0") == "200" or (code_gen or "0") == "200":
        print("App on port 5000 responds with 200 -> engine works.")
    else:
        print("App on port 5000 did not return 200 -> fix uWSGI/app first (see diagnose_uwsgi_exit_code.py).")
    if (code_https_root or "0") != "200" and (code_https_gen or "0") != "200":
        print("HTTPS did not return 200 -> nginx is not proxying to 127.0.0.1:5000 (or wrong server_name).")
        print("Fix: ensure location / and location /vidgenerator/ (and nested) use proxy_pass http://127.0.0.1:5000;")
        print("     run  python scripts/fix_nginx_proxy_all_pages.py   then  systemctl reload nginx")
    else:
        print("HTTPS returned 200 -> if the screen is still blank, check browser cache or JS errors.")
    if (code_5001 or "0") != "200" and nginx_5001_lines and "5001" in nginx_5001_lines:
        print("Port 5001 does not respond but nginx references 5001 -> APIs/static may 502/empty.")
        print("Fix: systemctl start uwsgi-vidgenerator-5001  OR  point those nginx locations to 5000/flask_backend only.")
    print("=" * 60)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fix Nginx for root-first setup (generator at masternoder.dk, not /vidgenerator).

Current problem: nginx redirects / to /vidgenerator/ and only proxies /vidgenerator/ to Flask,
so / and /generator never reach the app (404). This script rewrites nginx to proxy ALL
requests to the Flask app on 127.0.0.1:5000. The app then serves /, /generator, /static, /api
and returns 301 from /vidgenerator to /.

Run after deploying the new code:
  1. python scripts/deploy_all_and_restart_uwsgi.py
  2. python scripts/fix_nginx_root_proxy.py

Requires: paramiko, server credentials (DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASS).
"""
import paramiko
import os
import sys

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
NGINX_CONFIG = "/etc/nginx/sites-enabled/masternoder.dk"

# Proxy everything to Flask (app serves /, /generator, /static, /api; redirects /vidgenerator -> /)
PROXY_BLOCK = """        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        proxy_buffering off;
        proxy_request_buffering off;"""

LOCATION_BLOCKS = f'''    # All routes go to Flask (root, /generator, /static, /api, /vidgenerator redirects)
    location / {{
{PROXY_BLOCK}
    }}
'''

HTTPS_SERVER = f'''server {{
    listen 443 ssl http2;
    server_name masternoder.dk www.masternoder.dk;

    ssl_certificate /etc/letsencrypt/live/masternoder.dk/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/masternoder.dk/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

{LOCATION_BLOCKS}
}}
'''

HTTP_SERVER = '''server {
    listen 80;
    server_name masternoder.dk www.masternoder.dk;
    return 301 https://$host$request_uri;
}
'''

NEW_CONFIG = HTTPS_SERVER + "\n" + HTTP_SERVER


def main():
    dry_run = "--dry-run" in sys.argv
    print("=" * 60)
    print("Nginx: proxy all requests to Flask (root-first setup)")
    print("=" * 60)
    if dry_run:
        print("(dry-run: printing config only, no SSH)")
        print(NEW_CONFIG)
        return 0

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    except Exception as e:
        print(f"[ERROR] Connect failed: {e}")
        return 1

    def run(cmd, timeout=15):
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
        return out, err

    print(f"[1] Backup {NGINX_CONFIG} ...")
    run(f"cp {NGINX_CONFIG} {NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)")
    print("    OK")

    print("[2] Write new config (location / -> proxy to 127.0.0.1:5000) ...")
    sftp = ssh.open_sftp()
    with sftp.open(NGINX_CONFIG, "w") as f:
        f.write(NEW_CONFIG.encode("utf-8"))
    sftp.close()
    print("    OK")

    print("[3] nginx -t ...")
    out, err = run("nginx -t 2>&1")
    if "syntax is ok" not in out and "syntax is ok" not in err:
        print(f"    FAIL: {out or err}")
        ssh.close()
        return 1
    print("    OK")

    print("[4] systemctl reload nginx ...")
    run("systemctl reload nginx", timeout=10)
    print("    OK")

    ssh.close()
    print()
    print("Done. Test: https://masternoder.dk/ and https://masternoder.dk/generator")
    return 0


if __name__ == "__main__":
    sys.exit(main())

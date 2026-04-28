#!/usr/bin/env python3
"""
Setup Generator Page - No Cache (Server-Side Fix)

Research shows: HTTP Cache-Control headers from the server are the ONLY reliable
way to prevent browser caching. Meta tags and client-side hacks don't work for
initial load. This script configures nginx to send no-store for the generator page.

Run: python scripts/setup_generator_no_cache.py
Or: called automatically by deploy_vidgenerator_solution.py
"""
import os
import sys

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

# Nginx config snippets - prevent caching so UI updates deploy immediately
SERVICE_WORKER_NO_CACHE = '''
    # Service worker script: never cache - browser must always fetch latest for SW updates
    location = /vidgenerator/service-worker.js {
        add_header Cache-Control "no-store, no-cache, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
        alias /var/www/html/vidgenerator/service-worker.js;
    }
'''
# Proxy /api/* to Flask - fixes progression, templates (called with root baseUrl)
API_PROXY = '''
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
'''
# Proxy ALL /vidgenerator/api/* to Flask - fixes 404 for unified, monetization, notifications, etc.
VIDGENERATOR_API_PROXY = '''
    location /vidgenerator/api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
'''
GENERATOR_NO_CACHE = '''
    # Generator page: always no-cache so UI updates deploy immediately
    location /vidgenerator/generator {
        add_header Cache-Control "no-store, no-cache, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
'''
# Trophies and other key HTML: no-cache so browser interface updates after deploy
TROPHIES_NO_CACHE = '''
    # Trophies page: no-cache so UI updates deploy immediately
    location /vidgenerator/trophies {
        add_header Cache-Control "no-store, no-cache, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
'''
# Root vidgenerator (redirect/index): no-cache
VIDGENERATOR_ROOT_NO_CACHE = '''
    # Vidgenerator root/index: no-cache so UI updates deploy immediately
    location = /vidgenerator {
        add_header Cache-Control "no-store, no-cache, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location = /vidgenerator/ {
        add_header Cache-Control "no-store, no-cache, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
'''


def run():
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        return False

    ssh = None
    try:
        print("[setup_generator_no_cache] Connecting to", SERVER_HOST)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

        # Find nginx config (sites-available/default or masternoder.dk)
        for cfg in ["/etc/nginx/sites-available/default", "/etc/nginx/sites-available/masternoder.dk"]:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {cfg} && echo ok || true", timeout=5)
            if b"ok" in stdout.read():
                config_file = cfg
                break
        else:
            config_file = "/etc/nginx/sites-available/default"

        # Read config
        stdin, stdout, stderr = ssh.exec_command(f"cat {config_file}", timeout=10)
        config = stdout.read().decode("utf-8", errors="replace")

        # Check if all rules already present
        has_root_api = "location /api/ {" in config and "proxy_pass" in config
        has_api = "location /vidgenerator/api/" in config and "proxy_pass" in config
        has_gen = "location /vidgenerator/generator" in config and "no-store" in config
        has_trophies = "location /vidgenerator/trophies" in config and "no-store" in config
        has_sw = "location = /vidgenerator/service-worker.js" in config
        if has_root_api and has_api and has_gen and has_sw and has_trophies:
            print("[setup_generator_no_cache] All rules (api + generator + trophies + service-worker) already present")
            return True

        # Backup
        ssh.exec_command(f"cp {config_file} {config_file}.bak.$(date +%Y%m%d%H%M%S) 2>/dev/null || true", timeout=5)

        # Combined snippets (api proxies first - must intercept before static)
        snippets_to_add = ""
        if not has_root_api:
            snippets_to_add += API_PROXY
        if not has_api:
            snippets_to_add += VIDGENERATOR_API_PROXY
        if not has_sw:
            snippets_to_add += SERVICE_WORKER_NO_CACHE
        if not has_gen:
            snippets_to_add += GENERATOR_NO_CACHE
        if not has_trophies:
            snippets_to_add += TROPHIES_NO_CACHE

        # Insert before location /vidgenerator/ or at start of vidgenerator block
        if "location /vidgenerator/ {" in config:
            config = config.replace("    location /vidgenerator/ {", snippets_to_add + "    location /vidgenerator/ {")
        elif "location /vidgenerator" in config:
            config = config.replace("    location /vidgenerator", snippets_to_add + "    location /vidgenerator")
        else:
            import re
            config = re.sub(r"(\s+server_name\s+[^;]+;)", r"\1" + snippets_to_add, config, count=1)

        # Write
        sftp = ssh.open_sftp()
        with sftp.open(config_file, "w") as f:
            f.write(config)
        sftp.close()

        # Test
        stdin, stdout, stderr = ssh.exec_command("nginx -t 2>&1", timeout=10)
        out = (stdout.read() + stderr.read()).decode("utf-8", errors="replace")
        if "syntax is ok" not in out.lower():
            print("[setup_generator_no_cache] ERROR: nginx config invalid:", out[:300])
            return False

        # Reload
        ssh.exec_command("systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", timeout=15)
        print("[setup_generator_no_cache] Nginx updated and reloaded - generator page will not be cached")
        return True

    except Exception as e:
        print("[setup_generator_no_cache] ERROR:", e)
        import traceback
        traceback.print_exc()
        return False
    finally:
        if ssh:
            ssh.close()


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)

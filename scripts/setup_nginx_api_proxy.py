#!/usr/bin/env python3
"""
Setup Nginx API Proxy - Ensure /api/ and /vidgenerator/api/ are proxied to Flask.
Run this on the server or via deploy. Fixes 404 for unified, monetization, progression, etc.
"""
import os
import sys

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

# Only /vidgenerator/api/ - /api/ often already exists in nginx config
SNIPPET_CONTENT = '''
    # Vidgenerator API proxy - forward to Flask (python-proxy :5000)
    location /vidgenerator/api/ {
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
        print("[setup_nginx_api_proxy] Connecting to", SERVER_HOST)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

        # Create snippets dir
        ssh.exec_command("mkdir -p /etc/nginx/snippets", timeout=5)
        # Write snippet
        snippet_path = "/etc/nginx/snippets/vidgenerator-api-proxy.conf"
        sftp = ssh.open_sftp()
        with sftp.file(snippet_path, "w") as f:
            f.write(SNIPPET_CONTENT)
        sftp.close()
        print("[setup_nginx_api_proxy] Wrote", snippet_path)

        # Find main nginx site config
        for cfg in ["/etc/nginx/sites-available/masternoder.dk", "/etc/nginx/sites-available/default"]:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {cfg} && echo ok || true", timeout=5)
            if b"ok" in stdout.read():
                config_file = cfg
                break
        else:
            config_file = "/etc/nginx/sites-available/default"

        # Read config
        stdin, stdout, stderr = ssh.exec_command(f"cat {config_file}", timeout=10)
        config = stdout.read().decode("utf-8", errors="replace")

        # Check if vidgenerator api proxy already exists (avoid duplicate)
        if "location /vidgenerator/api/" in config and "proxy_pass" in config:
            print("[setup_nginx_api_proxy] location /vidgenerator/api/ already in config - skip")
            ssh.exec_command("systemctl reload nginx 2>&1", timeout=15)
            return True
        if "vidgenerator-api-proxy.conf" in config:
            print("[setup_nginx_api_proxy] Include already present")
        else:
            import re
            insert_line = "    include /etc/nginx/snippets/vidgenerator-api-proxy.conf;\n"
            # Insert after server_name line (most reliable)
            config = re.sub(
                r"(\s*server_name\s+[^;]+;)",
                r"\1\n" + insert_line,
                config,
                count=1
            )
            sftp = ssh.open_sftp()
            with sftp.open(config_file, "w") as f:
                f.write(config)
            sftp.close()
            print("[setup_nginx_api_proxy] Added include to", config_file)

        # Test nginx
        stdin, stdout, stderr = ssh.exec_command("nginx -t 2>&1", timeout=10)
        out = (stdout.read() + stderr.read()).decode("utf-8", errors="replace")
        if "syntax is ok" not in out.lower():
            print("[setup_nginx_api_proxy] ERROR nginx config invalid:", out[:500])
            return False

        ssh.exec_command("systemctl reload nginx 2>&1", timeout=15)
        print("[setup_nginx_api_proxy] Nginx reloaded - API proxy active")
        return True

    except Exception as e:
        print("[setup_nginx_api_proxy] ERROR:", e)
        import traceback
        traceback.print_exc()
        return False
    finally:
        if ssh:
            ssh.close()


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)

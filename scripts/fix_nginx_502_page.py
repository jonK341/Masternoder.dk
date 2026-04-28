#!/usr/bin/env python3
"""
Ensure nginx shows a stable "loading" page on 502/503/504 instead of a blank or generic error.
Uploads static/502.html to the server and adds error_page + location in the nginx server block.

Run from your PC:  python scripts/fix_nginx_502_page.py
Also run automatically from fix_502_nginx_only.py so ensure_site_up gives a stable screen.
"""
import os
import re
import sys
from pathlib import Path

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
NGINX_CONFIG = "/etc/nginx/sites-enabled/masternoder.dk"
REMOTE_502 = "/var/www/html/502.html"

# Snippet to add inside server { } (after opening brace). location = /502.html must come before location /.
ERROR_PAGE_LINE = "        error_page 502 503 504 /502.html;"
LOCATION_502_BLOCK = """        location = /502.html {
            root /var/www/html;
            internal;
        }"""


def main():
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)

    root = Path(__file__).resolve().parent.parent
    local_502 = root / "static" / "502.html"
    if not local_502.exists():
        print(f"[ERROR] Missing {local_502}")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    except Exception as e:
        print(f"[ERROR] SSH failed: {e}")
        sys.exit(1)

    def run(cmd, timeout=15):
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
        return out, err

    # 1. Upload 502.html to server
    print("Uploading static/502.html to", REMOTE_502)
    sftp = ssh.open_sftp()
    try:
        sftp.put(str(local_502), REMOTE_502)
    except Exception as e:
        print(f"[WARN] Upload failed: {e}. Ensure {REMOTE_502} exists on server.")
        run(f"mkdir -p /var/www/html && touch {REMOTE_502}")
        sftp.put(str(local_502), REMOTE_502)
    sftp.close()
    run(f"chown www-data:www-data {REMOTE_502} 2>/dev/null || true")

    # 2. Read current nginx config
    out, err = run(f"cat {NGINX_CONFIG}")
    if not out and err:
        print(f"[ERROR] Could not read {NGINX_CONFIG}: {err}")
        ssh.close()
        sys.exit(1)
    content = out

    # 3. Skip if already configured
    if "error_page 502" in content and "location = /502.html" in content:
        print("Nginx already serves 502.html on 502/503/504. Nothing to change.")
        ssh.close()
        sys.exit(0)

    # 4. Insert error_page and location = /502.html inside the server { } block for this site
    #    (so they appear before any "location /" – more specific first)
    lines = content.split("\n")
    insert_after = None
    first_server = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*server\s*\{", line):
            if first_server is None:
                first_server = i
            depth = 1
            j = i + 1
            while j < len(lines) and depth > 0:
                for c in lines[j]:
                    if c == "{": depth += 1
                    elif c == "}": depth -= 1
                if depth == 0:
                    block = "\n".join(lines[i:j + 1])
                    if "masternoder" in block.lower():
                        insert_after = i
                        break
                j += 1
            if insert_after is not None:
                break
    if insert_after is None:
        insert_after = first_server

    new_lines = []
    inserted = False
    for i, line in enumerate(lines):
        new_lines.append(line)
        if i == insert_after and not inserted:
            indent = "        "
            new_lines.append("")
            new_lines.append(indent + "error_page 502 503 504 /502.html;")
            new_lines.append(indent + "location = /502.html {")
            new_lines.append(indent + "    root /var/www/html;")
            new_lines.append(indent + "    internal;")
            new_lines.append(indent + "}")
            new_lines.append("")
            inserted = True

    if not inserted:
        print("[WARN] Could not find server { } block in nginx config. Skipping nginx patch.")
        ssh.close()
        sys.exit(0)

    new_content = "\n".join(new_lines)
    if new_content == content:
        ssh.close()
        sys.exit(0)

    # 5. Backup and write
    run(f"cp {NGINX_CONFIG} {NGINX_CONFIG}.bak.502 2>/dev/null || true")
    sftp = ssh.open_sftp()
    with sftp.file(NGINX_CONFIG, "w") as f:
        f.write(new_content)
    sftp.close()

    out, err = run("nginx -t 2>&1")
    if "syntax is ok" not in (out + err).lower() and "successful" not in (out + err).lower():
        print("[ERROR] nginx -t failed. Restoring backup.")
        run(f"cp {NGINX_CONFIG}.bak.502 {NGINX_CONFIG} 2>/dev/null || true")
        print(out or err)
        ssh.close()
        sys.exit(1)

    run("systemctl reload nginx 2>&1")
    print("Nginx now serves 502.html on 502/503/504. Users will see a stable loading page.")
    ssh.close()
    sys.exit(0)


if __name__ == "__main__":
    main()

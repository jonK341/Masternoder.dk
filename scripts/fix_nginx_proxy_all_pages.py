#!/usr/bin/env python3
"""
Fix nginx so ALL pages (including /vidgenerator/*) are proxied to the Flask app on port 5000.
If nginx has a location /vidgenerator/ that uses alias or try_files, only the front page
may work; other paths get 404. This script replaces such blocks with proxy_pass to the app.

Usage:
  python scripts/fix_nginx_proxy_all_pages.py
  python scripts/fix_nginx_proxy_all_pages.py --dry-run
"""
import re
import sys

SERVER_HOST = __import__("os").environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = __import__("os").environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))
NGINX_CONFIG = "/etc/nginx/sites-enabled/masternoder.dk"

# Standard proxy block for the app (so Flask serves all routes including /vidgenerator/*)
PROXY_BLOCK = """        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;"""


def find_location_blocks(content: str):
    """Find (start_line_idx, end_line_idx, location_match, block_content) for each location block."""
    lines = content.split("\n")
    i = 0
    blocks = []
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\s*)location\s+([^{]+)\s*\{?", line)
        if m:
            loc = m.group(2).strip()
            start = i
            depth = 0
            j = i
            while j < len(lines):
                for c in lines[j]:
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                if depth == 0:
                    blocks.append((start, j, loc, "\n".join(lines[start : j + 1])))
                    i = j
                    break
                j += 1
        i += 1
    return blocks


def block_uses_static(block_content: str) -> bool:
    """True if block uses alias, root, or try_files and has no proxy_pass (so we can add one)."""
    has_static = bool(re.search(r"\b(alias|root|try_files)\s+", block_content))
    has_any_proxy = "proxy_pass" in block_content
    return has_static and not has_any_proxy


def replace_block_with_proxy(content: str, start: int, end: int, location_spec: str) -> str:
    """Replace lines [start, end] with same location line but body = PROXY_BLOCK."""
    lines = content.split("\n")
    opening = lines[start]
    indent = re.match(r"^(\s*)", opening).group(1)
    new_block = [opening]
    for line in PROXY_BLOCK.split("\n"):
        new_block.append(indent + line.strip())
    new_block.append(indent + "}")
    new_lines = lines[:start] + new_block + lines[end + 1 :]
    return "\n".join(new_lines)


def main():
    dry_run = "--dry-run" in sys.argv
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)

    print("=" * 60)
    print("Fix nginx: proxy all pages to app (port 5000)")
    print("=" * 60)
    if dry_run:
        print("(dry-run: no changes written)")
    print()

    ssh = None
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    except Exception as e:
        print(f"[ERROR] Connect failed: {e}")
        sys.exit(1)

    def run(cmd, timeout=15):
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
        return out, err

    out, err = run(f"cat {NGINX_CONFIG}")
    if not out:
        print(f"[ERROR] Could not read {NGINX_CONFIG}: {err or 'empty file'}")
        ssh.close()
        sys.exit(1)
    original = out

    blocks = find_location_blocks(original)
    to_replace = []
    for start, end, loc, block_content in blocks:
        if "/vidgenerator" in loc or loc == "/" or loc == "~" or loc.startswith("~ "):
            if block_uses_static(block_content):
                to_replace.append((start, end, loc, block_content))

    if not to_replace:
        # Check if there's no proxy at all for /vidgenerator
        if "proxy_pass" in original and "5000" in original:
            print("Nginx already proxies to port 5000. No static-only /vidgenerator block found.")
            print("If pages still 404, ensure the Flask app (all_page_routes) is registered and deployed.")
        else:
            print("No location block using alias/root/try_files for /vidgenerator found.")
            print("Current config may already proxy everything, or structure differs.")
        print("\nCurrent location blocks (for reference):")
        out, _ = run("grep -n 'location\\|proxy_pass\\|try_files\\|alias\\|root ' " + NGINX_CONFIG + " 2>/dev/null | head -60")
        if out:
            for line in out.split("\n")[:50]:
                print("  ", line)
        ssh.close()
        sys.exit(0)

    # Replace from highest indices first so line numbers stay valid
    to_replace_sorted = sorted(to_replace, key=lambda x: -x[0])
    new_content = original
    for start, end, loc, block_content in to_replace_sorted:
        print(f"Replacing location {loc} (static) with proxy to 127.0.0.1:5000")
        new_content = replace_block_with_proxy(new_content, start, end, loc)

    if dry_run:
        print("\n[DRY-RUN] Would apply the above. Run without --dry-run to apply.")
        ssh.close()
        sys.exit(0)

    run(f"cp {NGINX_CONFIG} {NGINX_CONFIG}.bak.allpages 2>/dev/null || true")
    sftp = ssh.open_sftp()
    with sftp.file(NGINX_CONFIG, "w") as f:
        f.write(new_content)
    sftp.close()

    out, err = run("nginx -t 2>&1")
    combined = (out + " " + err).lower()
    if "syntax is ok" not in combined and "successful" not in combined:
        print("[ERROR] nginx -t failed. Restoring backup.")
        run(f"cp {NGINX_CONFIG}.bak.allpages {NGINX_CONFIG} 2>/dev/null || true")
        print("stdout:", out)
        print("stderr:", err)
        ssh.close()
        sys.exit(1)

    run("systemctl reload nginx 2>&1")
    print("\nNginx updated and reloaded. All pages should now proxy to the app.")
    ssh.close()
    sys.exit(0)


import os
if __name__ == "__main__":
    main()

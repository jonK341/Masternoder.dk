#!/usr/bin/env python3
"""
Diagnose 404 - then fix by ensuring nginx proxies ALL /vidgenerator/api/* to python-proxy :5000.
The key insight: /vidgenerator/api/generator/test works (returns 200) but /vidgenerator/api/unified/status 404.
This suggests nginx may have a SPECIFIC location for /vidgenerator/api/generator/ only, and other
/vidgenerator/api/* paths fall through to static files. We need a broader location for /vidgenerator/api/.
"""
import os
import re
import sys

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def sh(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out + ("\n" + err if err else "")


def main():
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    print("=" * 70)
    print("DIAGNOSE AND FIX 404 - VIDGENERATOR API")
    print("=" * 70)

    # 1. Test port 5000 directly
    print("\n[1] Test backend :5000 directly (bypass nginx):")
    for path in ["/api/unified/status", "/vidgenerator/api/unified/status", "/api/generator/test"]:
        code = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'http://127.0.0.1:5000{path}' 2>/dev/null")
        body = sh(ssh, f"curl -s 'http://127.0.0.1:5000{path}' 2>/dev/null | head -c 200")
        print(f"  {path}: {code}  {body[:80]}...")

    # 2. Show nginx location blocks for vidgenerator
    print("\n[2] Nginx location blocks for vidgenerator/api:")
    cfg = sh(ssh, "cat /etc/nginx/sites-enabled/masternoder.dk 2>/dev/null || cat /etc/nginx/sites-enabled/default 2>/dev/null")
    # Extract location blocks that mention vidgenerator or api
    for line in cfg.split("\n"):
        line = line.strip()
        if "location" in line and ("vidgenerator" in line or "api" in line):
            print(f"  {line}")
        if "proxy_pass" in line:
            print(f"    -> {line.strip()}")

    # 3. Check if /vidgenerator/api/ exists as a BROAD block (not just /vidgenerator/api/generator/)
    has_broad_vidgen_api = "location /vidgenerator/api/" in cfg and "location /vidgenerator/api/generator" not in cfg
    # Actually we need: is there a location that matches /vidgenerator/api/unified/ ?
    # location /vidgenerator/api/ would match /vidgenerator/api/unified/status
    # location /vidgenerator/api/generator would NOT match /vidgenerator/api/unified/
    if "location /vidgenerator/api/" in cfg:
        print("\n[3] Found location /vidgenerator/api/ - checking if it proxies to :5000")
        # Find the block and its proxy_pass
        in_block = False
        for line in cfg.split("\n"):
            if "location /vidgenerator/api/" in line:
                in_block = True
                print(f"  Block: {line.strip()}")
            elif in_block:
                if "proxy_pass" in line:
                    print(f"  proxy_pass: {line.strip()}")
                    if "5000" in line:
                        print("  -> Points to :5000 OK")
                    else:
                        print("  -> Does NOT point to :5000 - may need to change")
                    in_block = False
                elif line.strip().startswith("}"):
                    in_block = False
    else:
        print("\n[3] No location /vidgenerator/api/ found - only specific subpaths may be proxied")

    # 4. Fix: ensure location /vidgenerator/api/ proxies to 127.0.0.1:5000
    # If the backend :5000 returns 200 for /api/unified/status, nginx is the problem.
    # We'll add a location block that comes BEFORE more specific ones... actually nginx
    # uses longest prefix. So location /vidgenerator/api/generator/ would match before
    # location /vidgenerator/api/ for paths under generator. For /vidgenerator/api/unified/
    # we need location /vidgenerator/api/ to match. So we need a location /vidgenerator/api/
    # that proxies to 5000. The duplicate error said it exists. So maybe the existing one
    # points to the wrong backend. Let me try to REPLACE the proxy_pass in that block.
    print("\n[4] Attempting fix: ensure /vidgenerator/api/ proxies to 127.0.0.1:5000")
    config_file = "/etc/nginx/sites-available/masternoder.dk"
    if "masternoder" not in cfg:
        config_file = "/etc/nginx/sites-available/default"

    # Read current config
    cfg = sh(ssh, f"cat {config_file}", timeout=10)

    # Check: does location /vidgenerator/api/ proxy to something other than 5000?
    # We'll add a MORE SPECIFIC location for the paths that 404: /vidgenerator/api/unified/,
    # /vidgenerator/api/monetization/, etc. If we add location /vidgenerator/api/unified/
    # BEFORE location /vidgenerator/api/generator/, then... wait, /vidgenerator/api/unified/
    # wouldn't match /vidgenerator/api/generator/. So we need location /vidgenerator/api/
    # to catch all. The issue might be ORDER: if location /vidgenerator/ (static) comes
    # before location /vidgenerator/api/ in the config, does that matter? No - longest
    # prefix wins. /vidgenerator/api/ is longer than /vidgenerator/.

    # Alternative: maybe the config has location /vidgenerator/api/generator/ that proxies,
    # and location /vidgenerator/ for static. So /vidgenerator/api/unified/ matches
    # /vidgenerator/ (prefix) - the /vidgenerator/api/ part is still under /vidgenerator/.
    # For /vidgenerator/api/unified/status, which location wins?
    # - location /vidgenerator/api/generator/ - no, path doesn't start with generator
    # - location /vidgenerator/api/ - yes, matches
    # - location /vidgenerator/ - also matches but shorter
    # So we need location /vidgenerator/api/ to exist. If it doesn't, we add it.
    if "location /vidgenerator/api/" not in cfg or "location /vidgenerator/api/ {" not in cfg:
        # Add it - insert before location /vidgenerator/
        snippet = '''
    # Proxy ALL /vidgenerator/api/* to Flask (python-proxy :5000) - fixes unified, monetization, etc.
    location /vidgenerator/api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
'''
        # Insert before "location /vidgenerator/" - but we got duplicate before, so it exists
        # Try inserting before location /vidgenerator/ {
        new_cfg = cfg.replace("    location /vidgenerator/ {", snippet + "    location /vidgenerator/ {")
        if new_cfg != cfg:
            # Write backup and new config
            sh(ssh, f"cp {config_file} {config_file}.bak.diag", timeout=5)
            sftp = ssh.open_sftp()
            with sftp.open(config_file, "w") as f:
                f.write(new_cfg)
            sftp.close()
            print("  Added location /vidgenerator/api/ block")
        else:
            print("  Could not find insertion point")
    else:
        # Exists - ensure proxy_pass is 127.0.0.1:5000
        if "proxy_pass http://127.0.0.1:5000" not in cfg or "proxy_pass http://unix:" in cfg:
            print("  Location exists but may point to wrong backend - manual check needed")
        else:
            print("  Location /vidgenerator/api/ exists and points to :5000")
            print("  If still 404, the app on :5000 may not have these routes.")

    # 5. Test nginx and reload
    out = sh(ssh, "nginx -t 2>&1", timeout=10)
    print(f"\n[5] nginx -t: {out}")
    if "syntax is ok" in out.lower():
        sh(ssh, "systemctl reload nginx 2>&1", timeout=15)
        print("  Nginx reloaded")
    else:
        print("  Nginx config invalid - not reloading")

    # 6. Final test via public URL
    print("\n[6] Test via public URL (after fix):")
    # We can't easily curl public URL from server - user can verify

    ssh.close()
    print("\n" + "=" * 70)
    print("Run: curl -s -o /dev/null -w '%{http_code}' https://masternoder.dk/vidgenerator/api/unified/status")
    print("=" * 70)


if __name__ == "__main__":
    main()

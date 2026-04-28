#!/usr/bin/env python3
"""
Fix "conflicting server name masternoder.dk" by disabling duplicate nginx configs.

Run from your PC:  python scripts/fix_nginx_conflicting_server_name.py

Lists /etc/nginx/sites-enabled/, finds which configs define server_name masternoder.dk
or www.masternoder.dk, then disables duplicates so only one config handles the site.
Keeps the config that proxies to 127.0.0.1:5000 (the app); disables the rest.
"""
import os
import re
import sys

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = "root"
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
SITES_ENABLED = "/etc/nginx/sites-enabled"
SITES_AVAILABLE = "/etc/nginx/sites-available"
SERVER_NAMES = ("masternoder.dk", "www.masternoder.dk")
PROXY_5000 = re.compile(r"proxy_pass\s+http://127\.0\.0\.1:5000")


def run(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    try:
        out = stdout.read().decode(errors="replace").strip()
    except BaseException:
        out = ""
    try:
        err = stderr.read().decode(errors="replace").strip()
    except BaseException:
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
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    except Exception as e:
        print(f"[ERROR] SSH failed: {e}")
        sys.exit(1)

    print("=" * 60)
    print("Fix conflicting server_name (masternoder.dk)")
    print("=" * 60)

    # List enabled configs (symlinks or files)
    out, err = run(ssh, f"ls -la {SITES_ENABLED}/ 2>/dev/null")
    if not out and err:
        print(f"[ERROR] Cannot list {SITES_ENABLED}: {err}")
        ssh.close()
        sys.exit(1)

    lines = [l for l in out.splitlines() if l.strip()]
    # Parse: -rw-r--r-- 1 root root 1234 Mar 12 file  or  lrwxrwxrwx 1 root root 34 Mar 12 default -> ../sites-available/default
    enabled = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 5:
            if "->" in line:
                name = parts[-3]   # symlink: "... name -> target"
            else:
                name = parts[-1]
            if name in (".", "..") or name.startswith(".."):
                continue
            enabled.append(name)

    if not enabled:
        print("No configs in sites-enabled.")
        ssh.close()
        sys.exit(0)

    # For each enabled config, get content and check server_name + proxy_pass
    configs_with_domain = []  # (filename, has_proxy_5000, content_snippet)
    for name in enabled:
        path = f"{SITES_ENABLED}/{name}"
        out, _ = run(ssh, f"cat {path} 2>/dev/null")
        content = out or ""
        has_name = any(sn in content for sn in SERVER_NAMES)
        if not has_name:
            continue
        has_proxy = bool(PROXY_5000.search(content))
        configs_with_domain.append((name, has_proxy, content[:200]))

    if len(configs_with_domain) <= 1:
        print("No duplicate server_name found. Only one config defines masternoder.dk / www.masternoder.dk.")
        ssh.close()
        sys.exit(0)

    print(f"\nFound {len(configs_with_domain)} config(s) defining masternoder.dk / www.masternoder.dk:")
    for name, has_proxy, _ in configs_with_domain:
        role = " (proxies to 5000 – KEEP)" if has_proxy else " (no proxy to 5000)"
        print(f"  - {name}{role}")

    # Keep the one that has proxy_pass to 5000; if several, keep the first
    keep = None
    for name, has_proxy, _ in configs_with_domain:
        if has_proxy:
            keep = name
            break
    if keep is None:
        keep = configs_with_domain[0][0]
        print(f"\nNone proxy to 5000; keeping first: {keep}")

    to_disable = [name for name, _, _ in configs_with_domain if name != keep]
    if not to_disable:
        ssh.close()
        sys.exit(0)

    print(f"\nKeeping: {keep}")
    print(f"Disabling: {', '.join(to_disable)}")
    for name in to_disable:
        # Remove symlink in sites-enabled (do not delete file in sites-available)
        out, err = run(ssh, f"rm -f {SITES_ENABLED}/{name} 2>&1")
        if err and "No such file" not in err:
            print(f"  [WARN] {name}: {err}")
        else:
            print(f"  Disabled: {name}")

    out, err = run(ssh, "nginx -t 2>&1")
    combined = (out + " " + err).lower()
    if "syntax is ok" in combined or "successful" in combined:
        run(ssh, "systemctl reload nginx 2>&1")
        print("\nNginx reloaded. Conflicting server_name warnings should be gone.")
    else:
        print("\n[WARN] nginx -t failed. Re-enable configs if needed:")
        for name in to_disable:
            print(f"  ln -sf {SITES_AVAILABLE}/{name} {SITES_ENABLED}/{name}")

    ssh.close()


if __name__ == "__main__":
    main()

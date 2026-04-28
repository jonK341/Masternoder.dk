#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug production delivery of /vidgenerator/debugger

Compares:
- On-disk file contents markers
- nginx effective config (nginx -T) snippets
- curl headers/body via:
  - http://127.0.0.1:5000/debugger (app directly)
  - http://127.0.0.1/vidgenerator/debugger (nginx locally)
  - https://masternoder.dk/vidgenerator/debugger (public)
"""
import os
import re
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def _sh(ssh: paramiko.SSHClient, cmd: str, timeout: int = 20) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip()


def main() -> None:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    try:
        print("=" * 70)
        print("PRODUCTION DEBUGGER DELIVERY DIAGNOSTIC")
        print("=" * 70)

        path = "/var/www/html/vidgenerator/debugger/index.html"
        print("\n[1] On-disk file markers")
        head = _sh(ssh, f"python3 - <<'PY'\nimport pathlib\np=pathlib.Path('{path}')\nprint(p.exists())\nprint(p.stat().st_size)\nprint(p.stat().st_mtime)\ntext=p.read_text(encoding='utf-8', errors='replace')\nprint('has_cache_version', 'cache-version' in text)\nprint('has_aggressive', 'AGGRESSIVE CACHE-BUSTING' in text)\nprint('head_sample')\nprint(text[:220].replace('\\n','\\\\n'))\nPY", timeout=30)
        # Note: heredoc won't run on Windows locally; this runs on Linux server (bash).
        print(head)

        print("\n[2] Public fetch headers/body (server-side curl)")
        for label, url in [
            ("PUBLIC", "https://masternoder.dk/vidgenerator/debugger?diag=1"),
            ("NGINX_LOCAL", "http://127.0.0.1/vidgenerator/debugger?diag=1"),
            ("APP_LOCAL", "http://127.0.0.1:5000/debugger?diag=1"),
        ]:
            print(f"\n--- {label} {url}")
            hdrs = _sh(
                ssh,
                f"curl -sS -D - -o /tmp/dbg_body.html -H 'Cache-Control: no-cache' -H 'Pragma: no-cache' '{url}' | sed -n '1,25p'",
                timeout=30,
            )
            print(hdrs)
            body_probe = _sh(
                ssh,
                "python3 - <<'PY'\nfrom pathlib import Path\nb=Path('/tmp/dbg_body.html').read_text(encoding='utf-8', errors='replace')\nprint('len', len(b))\nprint('has_cache_version', 'cache-version' in b)\nprint('has_aggressive', 'AGGRESSIVE CACHE-BUSTING' in b)\nprint('head_sample', b[:220].replace('\\n','\\\\n'))\nPY",
                timeout=30,
            )
            print(body_probe)

        print("\n[3] nginx effective config snippets (nginx -T)")
        conf = _sh(ssh, "nginx -T 2>/dev/null | sed -n '1,200p'", timeout=30)
        print(conf[:2000])
        vid_lines = _sh(
            ssh,
            "nginx -T 2>/dev/null | grep -n \"location /vidgenerator/\\|expires\\|Cache-Control\\|add_header\\|proxy_pass\" | head -200",
            timeout=30,
        )
        print("\n-- matched lines --")
        print(vid_lines)

    finally:
        ssh.close()


if __name__ == "__main__":
    main()


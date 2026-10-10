#!/usr/bin/env python3
"""Install Phase 4 nginx snippet on camgirls.masternoder.dk (explorer + /app/ studio)."""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNIPPET_LOCAL = os.path.join(ROOT, "config", "nginx", "camgirls-phase4-app.conf.snippet")
REMOTE_SNIPPET = "/etc/nginx/snippets/masternoder-camgirls-phase4-app.conf"
VHOST_HINT = "/etc/nginx/sites-enabled/camgirls.masternoder.dk"


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Camgirls Phase 4 nginx /app/ proxy on server")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ask-pass", action="store_true")
    args = parser.parse_args()

    if not os.path.isfile(SNIPPET_LOCAL):
        print(f"Missing {SNIPPET_LOCAL}", file=sys.stderr)
        return 1
    with open(SNIPPET_LOCAL, "r", encoding="utf-8") as f:
        body = f.read()

    if args.dry_run:
        print("Would write:", REMOTE_SNIPPET)
        print(body)
        print(f"Would ensure {VHOST_HINT} includes: include {REMOTE_SNIPPET};")
        print("Verify: curl -sI https://camgirls.masternoder.dk/app/")
        return 0

    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from deploy_ssh_env import connect_deploy_ssh

    if args.ask_pass:
        os.environ.pop("DEPLOY_PASS", None)
        os.environ["_DEPLOY_ASK_PASS"] = "1"
    ssh, auth, _ = connect_deploy_ssh()
    print(f"[phase4] SSH via {auth}")

    escaped = body.replace("'", "'\"'\"'")
    import base64

    b64 = base64.b64encode(body.encode("utf-8")).decode("ascii")
    ssh.exec_command(
        f"echo {b64} | base64 -d | sudo tee {REMOTE_SNIPPET} > /dev/null && sudo chmod 644 {REMOTE_SNIPPET}",
        timeout=30,
    )
    patch = (
        f"if ! grep -q masternoder-camgirls-phase4-app {VHOST_HINT} 2>/dev/null; then "
        f"sudo sed -i '/server_name camgirls.masternoder.dk;/a \\    include {REMOTE_SNIPPET};' "
        f"{VHOST_HINT}; fi"
    )
    ssh.exec_command(patch, timeout=20)
    _, stdout, stderr = ssh.exec_command("sudo nginx -t && sudo systemctl reload nginx", timeout=30)
    out = (stdout.read() + stderr.read()).decode(errors="replace")
    print(out)
    _, stdout, _ = ssh.exec_command(
        "curl -s -o /dev/null -w '%{http_code}' -H 'Host: camgirls.masternoder.dk' "
        "http://127.0.0.1/app/",
        timeout=20,
    )
    code = (stdout.read() or b"").decode().strip()
    print(f"[phase4] local probe /app/ HTTP {code}")
    ssh.close()
    return 0 if code in ("200", "301", "302") else 1


if __name__ == "__main__":
    raise SystemExit(main())

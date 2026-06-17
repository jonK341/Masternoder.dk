#!/usr/bin/env python3
"""Post-deploy smoke checks for camgirls catalog, agents, and page route."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DEFAULT_BASE = os.environ.get("POST_DEPLOY_BASE_URL", "https://masternoder.dk").rstrip("/")


def _fetch(url: str, *, timeout: int = 25) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "camgirls-post-deploy-verify/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return 0, str(exc)


def _check_json(label: str, url: str, *, expect_keys: list[str]) -> bool:
    status, body = _fetch(url)
    ok = True
    print(f"\n=== {label} ===")
    print(f"GET {url}")
    print(f"HTTP {status}")
    if status != 200:
        print(body[:500])
        return False
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print("Invalid JSON")
        return False
    for key in expect_keys:
        if key not in data:
            print(f"Missing key: {key}")
            ok = False
    if data.get("success") is False:
        print(f"success=false error={data.get('error')}")
        ok = False
    print(json.dumps({k: data.get(k) for k in expect_keys if k in data}, indent=2)[:800])
    return ok


def verify_public(base: str) -> int:
    base = base.rstrip("/")
    checks = [
        ("performers", f"{base}/api/camgirls/performers?user_id=post_deploy_verify", ["success", "performers"]),
        ("agents", f"{base}/api/camgirls/agents", ["success", "agents"]),
        ("agent-tools", f"{base}/api/camgirls/agent-tools", ["success", "tools"]),
    ]
    page_status, page_body = _fetch(f"{base}/camgirls/")
    print("\n=== page /camgirls/ ===")
    print(f"GET {base}/camgirls/")
    print(f"HTTP {page_status}")
    page_ok = page_status == 200 and "Camgirls" in page_body

    results = [page_ok]
    for label, url, keys in checks:
        results.append(_check_json(label, url, expect_keys=keys))

    passed = sum(results)
    total = len(results)
    print(f"\nResult: {passed}/{total} checks passed")
    return 0 if passed == total else 1


def verify_remote(*, force_prompt: bool = False) -> int:
    try:
        import paramiko
    except ImportError:
        print("paramiko required for --remote", file=sys.stderr)
        return 1

    try:
        import dotenv

        dotenv.load_dotenv(os.path.join(ROOT, ".env"))
    except Exception:
        pass

    from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

    pw = require_deploy_pass(force_prompt=force_prompt)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)

    def sh(cmd: str) -> str:
        _, stdout, stderr = ssh.exec_command(cmd, timeout=90)
        return (stdout.read() + stderr.read()).decode(errors="replace").strip()

    web = "/var/www/html"
    cmds = [
        ("local performers", "curl -s -w '\\nHTTP:%{http_code}' 'http://127.0.0.1:5000/api/camgirls/performers?user_id=verify'"),
        ("local agents", "curl -s -w '\\nHTTP:%{http_code}' http://127.0.0.1:5000/api/camgirls/agents"),
        ("local page", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/camgirls/"),
        ("routes", f"cd {web} && PY=$(test -x .venv/bin/python && echo .venv/bin/python || echo python3) && "
         f"$PY -c \"import sys; sys.path.insert(0,'{web}'); "
         "from vidgenerator import create_app; app=create_app(); "
         "print([str(r) for r in app.url_map.iter_rules() if 'camgirl' in str(r)])\""),
        ("payout ops", "curl -s http://127.0.0.1:5000/api/camgirls/ops/payout-addresses 2>&1 | head -c 400"),
    ]
    for label, cmd in cmds:
        print(f"\n=== remote {label} ===")
        print(sh(cmd))
    ssh.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify camgirls deploy")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="Public origin (default masternoder.dk)")
    parser.add_argument("--remote", action="store_true", help="SSH curl checks on server :5000")
    parser.add_argument("--remote-only", action="store_true", help="Skip public HTTPS checks")
    parser.add_argument("--ask-pass", action="store_true", help="Prompt for SSH password (remote checks)")
    args = parser.parse_args()

    codes = []
    if not args.remote_only:
        codes.append(verify_public(args.base_url))
    if args.remote or args.remote_only:
        codes.append(verify_remote(force_prompt=args.ask_pass))
    return 0 if all(c == 0 for c in codes) else 1


if __name__ == "__main__":
    raise SystemExit(main())

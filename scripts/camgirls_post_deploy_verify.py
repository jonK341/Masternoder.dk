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

WEB = "/var/www/html"


def _default_base() -> str:
    explicit = (os.environ.get("POST_DEPLOY_BASE_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    # On the server, hit uWSGI directly — avoids slow/hanging public HTTPS from localhost.
    if os.path.isdir(WEB) and os.path.abspath(ROOT).startswith(WEB):
        return "http://127.0.0.1:5000"
    return "https://masternoder.dk"


def _ops_secret_prefix(web: str = WEB) -> str:
    return (
        f"source {web}/cron/mn2_read_ops_secret.sh 2>/dev/null; "
        "SECRET=$(mn2_read_ops_secret 2>/dev/null || true)"
    )


def _fetch(url: str, *, timeout: int | None = None) -> tuple[int, str]:
    if timeout is None:
        timeout = 25 if "127.0.0.1" in url or "localhost" in url else 60
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "camgirls-post-deploy-verify/1.0", "Connection": "close"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return 0, str(exc)


def _json_success(body: str) -> bool:
    try:
        data = json.loads(body)
        return bool(data.get("success"))
    except json.JSONDecodeError:
        return False


def _curl_json_ok(body: str) -> bool:
    line = body.split("HTTP:")[0].strip()
    return _json_success(line)


def _performer_count_ok(body: str, minimum: int = 5) -> bool:
    line = body.split("HTTP:")[0].strip() if "HTTP:" in body else body.strip()
    try:
        data = json.loads(line)
        return int(data.get("count") or 0) >= minimum
    except (json.JSONDecodeError, TypeError, ValueError):
        return False


def _check_json(
    label: str,
    url: str,
    *,
    expect_keys: list[str],
    retries: int = 3,
    retry_sleep: float = 2.0,
) -> bool:
    import time

    print(f"\n=== {label} ===")
    print(f"GET {url}")
    last_status, last_body = 0, ""
    for attempt in range(1, max(1, retries) + 1):
        status, body = _fetch(url)
        last_status, last_body = status, body
        if attempt > 1:
            print(f"retry {attempt}/{retries} HTTP {status}")
        else:
            print(f"HTTP {status}")
        if status != 200:
            if attempt < retries:
                time.sleep(retry_sleep)
                continue
            print(body[:500])
            return False
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            if attempt < retries:
                time.sleep(retry_sleep)
                continue
            print("Invalid JSON")
            return False
        ok = True
        for key in expect_keys:
            if key not in data:
                print(f"Missing key: {key}")
                ok = False
        if data.get("success") is False:
            print(f"success=false error={data.get('error')}")
            ok = False
        if ok:
            print(json.dumps({k: data.get(k) for k in expect_keys if k in data}, indent=2)[:800])
            return True
        if attempt < retries:
            time.sleep(retry_sleep)
    print(last_body[:500] if last_body else f"last HTTP {last_status}")
    return False


def _warm_public(base: str, *, rounds: int = 2) -> None:
    """Prime nginx/uwsgi workers before strict verify (lazy load + dual upstream)."""
    import time

    urls = [
        f"{base}/api/camgirls/agent-tools",
        f"{base}/api/camgirls/agents",
        f"{base}/api/camgirls/performers?user_id=warmup&lite=1",
    ]
    print(f"\n=== warmup ({rounds} round(s)) ===")
    for r in range(1, rounds + 1):
        for url in urls:
            status, _ = _fetch(url, timeout=45)
            print(f"  r{r} {status} {url.split(base)[-1]}")
            time.sleep(0.5)


def verify_public(base: str, *, retries: int = 3, warmup_rounds: int = 0) -> int:
    base = base.rstrip("/")
    if warmup_rounds > 0:
        _warm_public(base, rounds=warmup_rounds)
    checks = [
        (
            "performers",
            f"{base}/api/camgirls/performers?user_id=post_deploy_verify&lite=1",
            ["success", "performers"],
        ),
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
        results.append(_check_json(label, url, expect_keys=keys, retries=retries))

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

    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

    pw = require_deploy_pass(force_prompt=force_prompt)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)

    secret = _ops_secret_prefix()

    def sh(cmd: str, timeout: int = 90) -> tuple[int, str]:
        _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        code = stdout.channel.recv_exit_status()
        text = (stdout.read() + stderr.read()).decode(errors="replace").strip()
        return code, text

    # HTTP-only checks — uwsgi already proves routes; no Flask import on system python3.
    checks: list[tuple[str, str, object]] = [
        (
            "local performers",
            "curl -s -w '\\nHTTP:%{http_code}' 'http://127.0.0.1:5000/api/camgirls/performers?user_id=verify'",
            lambda body: _curl_json_ok(body),
        ),
        (
            "local agents",
            "curl -s -w '\\nHTTP:%{http_code}' http://127.0.0.1:5000/api/camgirls/agents",
            lambda body: _curl_json_ok(body),
        ),
        (
            "local page",
            "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/camgirls/",
            lambda body: body.strip() == "200",
        ),
        (
            "agent-tools route",
            "curl -s http://127.0.0.1:5000/api/camgirls/agent-tools",
            _json_success,
        ),
        (
            "chat route",
            "curl -s -o /dev/null -w '%{http_code}' -X POST "
            "http://127.0.0.1:5000/api/camgirls/chat -H 'Content-Type: application/json' -d '{}'",
            lambda body: body.strip() in ("400", "403", "200"),
        ),
        (
            "blueprint registered",
            f"grep -q camgirls {WEB}/backend/register_blueprints.py && echo registered",
            lambda body: "registered" in body,
        ),
        (
            "payout addresses",
            f"{secret}; curl -s -H \"X-Ops-Secret: $SECRET\" "
            "http://127.0.0.1:5000/api/camgirls/ops/payout-addresses",
            _json_success,
        ),
        (
            "payout provision",
            f"{secret}; curl -s -X POST -H \"X-Ops-Secret: $SECRET\" "
            "http://127.0.0.1:5000/api/camgirls/ops/payout-addresses",
            _json_success,
        ),
        (
            "studio catalog",
            "curl -s http://127.0.0.1:5000/api/camgirls/studio/catalog",
            lambda body: _json_success(body) and '"moods"' in body,
        ),
        (
            "performer count",
            "curl -s 'http://127.0.0.1:5000/api/camgirls/performers?user_id=verify'",
            lambda body: _performer_count_ok(body, 5),
        ),
        (
            "favorite route",
            "curl -s -o /dev/null -w '%{http_code}' -X POST "
            "http://127.0.0.1:5000/api/camgirls/performers/performer_nova/favorite "
            "-H 'Content-Type: application/json' -d '{}'",
            lambda body: body.strip() == "200",
        ),
    ]

    passed = 0
    for label, cmd, ok_fn in checks:
        print(f"\n=== remote {label} ===")
        code, body = sh(cmd)
        print(body)
        ok = ok_fn(body) if label in (
            "chat route", "blueprint registered", "local page", "favorite route",
        ) else (code == 0 and ok_fn(body))
        print(f"{'PASS' if ok else 'FAIL'} (exit {code})")
        if ok:
            passed += 1

    ssh.close()
    total = len(checks)
    print(f"\nRemote result: {passed}/{total} checks passed")
    return 0 if passed == total else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify camgirls deploy")
    parser.add_argument("--base-url", default=_default_base(), help="API origin (auto 127.0.0.1:5000 on server)")
    parser.add_argument("--remote", action="store_true", help="SSH curl checks on server :5000")
    parser.add_argument("--remote-only", action="store_true", help="Skip public HTTPS checks")
    parser.add_argument("--ask-pass", action="store_true", help="Prompt for SSH password (remote checks)")
    parser.add_argument("--retries", type=int, default=3, help="Retries per public JSON check (default 3)")
    parser.add_argument(
        "--warmup-rounds",
        type=int,
        default=0,
        help="Hit agent-tools/agents/lite performers N times before verify (public HTTPS)",
    )
    args = parser.parse_args()

    codes = []
    if not args.remote_only:
        codes.append(verify_public(args.base_url, retries=args.retries, warmup_rounds=args.warmup_rounds))
    if args.remote or args.remote_only:
        codes.append(verify_remote(force_prompt=args.ask_pass))
    return 0 if all(c == 0 for c in codes) else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
HTTP smoke checks for key platform surfaces: APIs used by gallery, shop, leaderboards,
agents, starmap, themes, generator health, and static HTML routes.

Usage:
  set PLATFORM_BASE_URL=https://your-host   (default http://127.0.0.1:5000)
  python scripts/service_check_all_components.py

  # Skip SSL cert verification (when testing prod from dev, self-signed certs)
  set PLATFORM_CHECK_SSL_VERIFY=0

  # Per-request timeout (default 30s). /api/shop/payment-health can wait ~30s server-side
  # for MN2 RPC — client timeout is auto-bumped to at least 65s for that path.
  set PLATFORM_CHECK_TIMEOUT=30

  # Skip slow endpoints (MN2 / heavy generator): payment-health, integration-health, generation-health
  set PLATFORM_SKIP_SLOW_CHECKS=1

  # Restart uWSGI on the server via SSH, then run checks (loads new Python code):
  python scripts/service_check_all_components.py --restart-uwsgi
  python scripts/service_check_all_components.py --restart-uwsgi --restart-5001 --wait-after-restart 60

  # Same via env (e.g. CI):
  set PLATFORM_RESTART_UWSGI=1

  # Tip: On the server: PLATFORM_BASE_URL=http://127.0.0.1:5000 python ...
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Any

BASE = os.environ.get("PLATFORM_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
TIMEOUT = float(os.environ.get("PLATFORM_CHECK_TIMEOUT", "30"))
SSL_VERIFY = os.environ.get("PLATFORM_CHECK_SSL_VERIFY", "1") not in ("0", "false", "no")
SKIP_SLOW = os.environ.get("PLATFORM_SKIP_SLOW_CHECKS", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# Paths where the server may block on MN2 RPC (~30s) or heavy work
_SLOW_PATH_PREFIXES = (
    "/api/shop/payment-health",
    "/api/shop/integration-health",
    "/api/generator/generation-health",
)


def _ssh_restart_uwsgi(restart_5001: bool) -> bool:
    """Restart uwsgi-vidgenerator (+ optional 5001) on DEPLOY_HOST. Same credentials as scripts/deploy.py."""
    try:
        import paramiko
    except ImportError:
        print("Install paramiko for --restart-uwsgi: pip install paramiko", flush=True)
        return False
    host = os.environ.get("DEPLOY_HOST", "masternoder.dk")
    user = os.environ.get("DEPLOY_USER", "root")
    password = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
    print(f"SSH {user}@{host} — restarting uwsgi-vidgenerator" + (" + uwsgi-vidgenerator-5001" if restart_5001 else ""), flush=True)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=password, timeout=45)
    except Exception as e:
        print(f"[ERROR] SSH connect: {e}", flush=True)
        return False
    cmds = [
        "systemctl restart uwsgi-vidgenerator 2>&1",
    ]
    if restart_5001:
        cmds.append("systemctl restart uwsgi-vidgenerator-5001 2>&1 || true")
    for c in cmds:
        _, stdout, stderr = ssh.exec_command(c, timeout=120)
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
        if out:
            print(out, flush=True)
        if err:
            print(err, flush=True)
    ssh.close()
    return True


def _effective_timeout(path: str) -> float:
    t = TIMEOUT
    for prefix in _SLOW_PATH_PREFIXES:
        if path.startswith(prefix):
            return max(t, 65.0)
    return t


def _req(method: str, path: str, data: dict | None = None) -> tuple[int, Any]:
    url = BASE + path
    body = None
    headers = {"Accept": "application/json", "User-Agent": "MasterNoder-ServiceCheck/1.0"}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, method=method, headers=headers)
    ctx = None
    if url.startswith("https://") and not SSL_VERIFY:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    timeout = _effective_timeout(path)
    try:
        with urllib.request.urlopen(r, timeout=timeout, context=ctx) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            code = resp.getcode()
            try:
                return code, json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError:
                return code, raw[:500]
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            raw = ""
        return e.code, raw[:300]
    except Exception as e:
        err = str(e)
        return -1, err if err else repr(e)


def main(
    *,
    restart_uwsgi: bool = False,
    restart_5001: bool = False,
    wait_after_restart: float = 45.0,
) -> int:
    checks: list[tuple[str, str, Any]] = []

    def ok(name: str, path: str, expect: Any = None) -> None:
        print(f"  .. {name}", flush=True)
        code, payload = _req("GET", path)
        good = 200 <= code < 300
        if good and expect is not None:
            if callable(expect):
                good = bool(expect(payload))
            elif isinstance(expect, dict) and isinstance(payload, dict):
                good = all(payload.get(k) == v for k, v in expect.items())
        detail = f"{code} {path}"
        if code == -1 and isinstance(payload, str):
            detail += f" — {payload[:120]}"
        checks.append((name, detail, good))

    def say(*args: Any) -> None:
        print(*args, flush=True)

    say("Base URL:", BASE)
    if BASE.startswith("https://"):
        say("SSL verify:", "on" if SSL_VERIFY else "off (PLATFORM_CHECK_SSL_VERIFY=0)")
    say("Timeout:", TIMEOUT, "s (slow paths auto >= 65s)")
    if SKIP_SLOW:
        say("PLATFORM_SKIP_SLOW_CHECKS=1 - skipping MN2/heavy generator checks")
    say()

    if restart_uwsgi:
        if not _ssh_restart_uwsgi(restart_5001):
            return 1
        say(f"Waiting {wait_after_restart}s for uWSGI workers to load...")
        time.sleep(max(0.0, float(wait_after_restart)))
        say()

    ok(
        "API health (fast)",
        "/api/health",
        lambda p: isinstance(p, dict) and p.get("success") and p.get("status") == "healthy",
    )
    ok(
        "Leaderboard categories",
        "/api/leaderboard/categories",
        lambda p: isinstance(p, dict)
        and p.get("success")
        and isinstance(p.get("categories"), list)
        and len(p.get("categories") or []) >= 3,
    )
    ok(
        "Leaderboard all",
        "/api/leaderboard/all?limit=5",
        lambda p: isinstance(p, dict)
        and p.get("success")
        and isinstance(p.get("leaderboard"), list),
    )
    ok(
        "Leaderboard generation slice",
        "/api/leaderboard/generation?limit=5",
        lambda p: isinstance(p, dict)
        and p.get("success")
        and isinstance(p.get("leaderboard"), list)
        and p.get("system") == "generation",
    )
    ok("Themes list", "/api/themes/list", lambda p: isinstance(p, dict) and p.get("success"))
    ok("Themes user", "/api/themes/user?user_id=default_user", lambda p: isinstance(p, dict) and p.get("success"))
    ok("Star Map 25 data", "/api/star-map/25", lambda p: isinstance(p, dict) and p.get("success"))
    ok("Star Map 25 status", "/api/star-map/25/status?user_id=default_user", lambda p: isinstance(p, dict) and p.get("success"))
    ok("Agents my-agents", "/api/agents/my-agents?user_id=default_user", lambda p: isinstance(p, dict) and "agents" in p)
    ok("Gallery list", "/api/gallery/list?limit=1", lambda p: isinstance(p, dict))
    ok("Shop v3 items", "/api/shop-v3/items", lambda p: isinstance(p, dict))
    ok(
        "Shop config",
        "/api/shop/config",
        lambda p: isinstance(p, dict) and p.get("success") and "use_shop_v3" in p,
    )
    if not SKIP_SLOW:
        ok(
            "Shop payment health",
            "/api/shop/payment-health",
            lambda p: isinstance(p, dict)
            and p.get("success")
            and isinstance(p.get("mn2_daemon"), dict)
            and isinstance(p.get("paypal"), dict),
        )
        ok(
            "Shop integration (generator + media)",
            "/api/shop/integration-health",
            lambda p: isinstance(p, dict)
            and p.get("success")
            and isinstance(p.get("shop"), dict)
            and isinstance(p.get("generator"), dict),
        )
    ok("Points comprehensive", "/api/points/comprehensive?user_id=default_user", lambda p: isinstance(p, dict))
    if not SKIP_SLOW:
        ok("Generator generation-health", "/api/generator/generation-health", lambda p: isinstance(p, dict))

    # Static HTML (200 and HTML body)
    for label, path, min_len in [
        ("Page gallery", "/gallery", 200),
        ("Page shop", "/shop", 200),
        ("Page starmap25", "/starmap25", 200),
        ("Page leaderboards", "/leaderboards", 200),
        ("Page agents", "/agents", 500),  # real agents page; avoid false OK on tiny stub
        ("Page metal", "/metal", 200),
    ]:
        print(f"  .. {label}", flush=True)
        code, payload = _req("GET", path)
        html_ok = 200 <= code < 300 and (isinstance(payload, str) or (isinstance(payload, dict) and not payload))
        if 200 <= code < 300 and not isinstance(payload, str):
            html_ok = False
        if html_ok and isinstance(payload, str) and len(payload) < min_len:
            html_ok = False
        detail = f"{code} {path}"
        if code == -1 and isinstance(payload, str):
            detail += f" — {payload[:120]}"
        checks.append((label, detail, html_ok))

    failed = 0
    for name, detail, good in checks:
        status = "OK" if good else "FAIL"
        if not good:
            failed += 1
        print(f"[{status}] {name}: {detail}", flush=True)

    print(flush=True)
    if failed:
        print(f"{failed} check(s) failed.", flush=True)
        return 1
    print("All checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="HTTP smoke checks for MasterNoder.dk (optionally restart uwsgi via SSH first).",
    )
    parser.add_argument(
        "--restart-uwsgi",
        action="store_true",
        help="SSH to server and systemctl restart uwsgi-vidgenerator before checks (loads new code after upload-only deploy).",
    )
    parser.add_argument(
        "--restart-5001",
        action="store_true",
        help="Also restart uwsgi-vidgenerator-5001 (second backend).",
    )
    parser.add_argument(
        "--wait-after-restart",
        type=float,
        default=45.0,
        metavar="SEC",
        help="Seconds to sleep after restart before HTTP checks (default 45).",
    )
    args = parser.parse_args()
    env_restart = os.environ.get("PLATFORM_RESTART_UWSGI", "").strip().lower() in ("1", "true", "yes", "on")
    sys.exit(
        main(
            restart_uwsgi=bool(args.restart_uwsgi or env_restart),
            restart_5001=bool(args.restart_5001),
            wait_after_restart=float(args.wait_after_restart),
        )
    )

#!/usr/bin/env python3
"""Verify Discord setup — local .env + production endpoints."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

BASE = (os.environ.get("SOCIAL_AUTH_BASE_URL") or "https://masternoder.dk").rstrip("/")

CHECKS = [
    ("interactions", f"{BASE}/api/discord/interactions"),
    ("controller", f"{BASE}/api/discord/controller/status"),
    ("portal-urls", f"{BASE}/api/discord/setup/portal-urls"),
    ("terms", f"{BASE}/legal/terms/"),
    ("privacy", f"{BASE}/legal/privacy/"),
    ("verify-page", f"{BASE}/discord/verify/"),
    ("role-callback", f"{BASE}/api/discord/role-connection/callback"),
    ("icon", f"{BASE}/static/discord-branding/discord-app-icon.png"),
]


def main() -> int:
    import requests
    from backend.services.discord_setup_service import validate_env_config

    print("=== Local .env ===")
    env = validate_env_config()
    for issue in env.get("issues") or []:
        print(f"  WARN: {issue}")
    if env.get("success"):
        print("  OK: all required Discord env keys present")
    cfg = env.get("configured") or {}
    print(f"  bot_token: {cfg.get('bot_token')}")
    print(f"  application_id: {cfg.get('application_id')}")
    print(f"  public_key: {cfg.get('public_key')}")
    print(f"  guild_id: {cfg.get('guild_id')}")

    print("\n=== Production URLs ===")
    fails = 0
    for name, url in CHECKS:
        try:
            r = requests.get(url, timeout=25, allow_redirects=True)
            auto = "auto_fixed" in (r.text or "")
            ok = r.status_code == 200 and not auto
            if name in ("terms", "privacy", "verify-page", "icon"):
                ok = r.status_code == 200 and "text/html" in (r.headers.get("Content-Type") or "") or "image/" in (r.headers.get("Content-Type") or "")
            if name == "icon":
                ok = r.status_code == 200
            status = "OK" if ok else "FAIL"
            if not ok:
                fails += 1
            print(f"  [{status}] {name}: {r.status_code} {url}")
            if auto:
                print("         still auto-fix stub — deploy mn2_staking + mn2_env")
            if name == "interactions" and r.status_code == 200:
                try:
                    j = r.json()
                    print(f"         service={j.get('service')}")
                except Exception:
                    pass
            if name == "controller" and r.status_code == 200:
                try:
                    j = r.json()
                    print(f"         bot_token_configured={j.get('bot_token_configured')}")
                except Exception:
                    pass
        except Exception as exc:
            fails += 1
            print(f"  [FAIL] {name}: {exc}")

    print(f"\n=== Summary: {len(CHECKS) - fails}/{len(CHECKS)} passed ===")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

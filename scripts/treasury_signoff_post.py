#!/usr/bin/env python3
"""POST treasury sign-off to production API (uses ops secret from .env)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    import dotenv
    dotenv.load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

COLD = "JJvVw8MeVevRuziARDxAouAN2EuUCPSnTQ"
BODY = {
    "approver": "Jon",
    "cold_wallet_address": COLD,
    "max_batch_mn2": 600000,
    "notes": "MN2_OPS §8.6 treasury sign-off",
}


def _secret() -> str:
    for key in ("DISCORD_OPS_SECRET", "ADMIN_OPS_SECRET", "MN2_OPS_SECRET"):
        v = (os.environ.get(key) or "").strip()
        if v:
            return v
    return ""


def post(base: str, secret: str) -> tuple[int, str]:
    url = base.rstrip("/") + "/api/agents/treasury/sign-off"
    data = json.dumps(BODY).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Ops-Secret"] = secret
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def main() -> int:
    secret = _secret()
    if not secret:
        print("No DISCORD_OPS_SECRET / ADMIN_OPS_SECRET / MN2_OPS_SECRET in .env")
        return 1

    for base in ("https://masternoder.dk", "http://masternoder.dk"):
        code, text = post(base, secret)
        print(f"POST {base}/api/agents/treasury/sign-off -> HTTP {code}")
        try:
            print(json.dumps(json.loads(text), indent=2))
        except Exception:
            print(text[:2000])
        if code == 200:
            try:
                if json.loads(text).get("success"):
                    return 0
            except Exception:
                pass
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

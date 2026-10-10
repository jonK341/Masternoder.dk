#!/usr/bin/env python3
"""Quick production check for monetization security patch."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "https://masternoder.dk"


def call(method: str, path: str, data: dict | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"raw": raw[:400]}


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    st, d = call("GET", "/api/shop/battle-pass?user_id=deploy_verify_user")
    checks.append(
        (
            "battle_pass_status",
            st == 200 and bool(d.get("success")),
            f"st={st} season={d.get('season_id')}",
        )
    )

    st, d = call(
        "POST",
        "/api/shop/battle-pass/purchase",
        {"user_id": "deploy_verify_user", "source": "paypal"},
    )
    checks.append(
        (
            "paypal_source_blocked",
            st == 400 and d.get("code") == "PAYPAL_CHECKOUT_REQUIRED",
            f"st={st} code={d.get('code')}",
        )
    )

    st, d = call("POST", "/api/shop/battle-pass/purchase", {"user_id": "deploy_verify_user"})
    checks.append(
        (
            "coin_purchase_not_free",
            st in (400, 403),
            f"st={st} err={d.get('error') or d.get('code')}",
        )
    )

    st, d = call(
        "POST",
        "/api/casino/mn2/buyin",
        {"user_id": "deploy_verify_user", "pack_id": "mn2-buyin-starter"},
    )
    checks.append(
        (
            "mn2_buyin_gated",
            st in (400, 403),
            f"st={st} code={d.get('code')} err={d.get('error')}",
        )
    )

    st, d = call("GET", "/api/camgirls/livekit/status")
    checks.append(
        (
            "livekit_status",
            st == 200 and bool(d.get("success")),
            f"mode={d.get('mode')}",
        )
    )

    st, d = call("GET", "/api/health")
    checks.append(("health", st == 200, f"status={d.get('status')}"))

    print("=== Production security deploy verify ===")
    all_ok = True
    for name, ok, detail in checks:
        if not ok:
            all_ok = False
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")

    print("OVERALL:", "ALL PASS" if all_ok else "SOME FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

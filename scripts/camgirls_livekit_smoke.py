#!/usr/bin/env python3
"""Smoke LiveKit camgirls routes (status + token gate)."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as resp:
        return json.loads(resp.read().decode())


def _post(url: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return exc.code, payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://masternoder.dk")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    status = _get(f"{base}/api/camgirls/livekit/status")
    print("status:", json.dumps(status, indent=2))
    if not status.get("success"):
        return 1
    code, tok = _post(
        f"{base}/api/camgirls/livekit/token",
        {"user_id": "livekit_smoke", "performer_id": "performer_nova"},
    )
    print("token http", code, json.dumps(tok, indent=2))
    if status.get("mode") == "live":
        if code != 403 and not (tok.get("success") and tok.get("token")):
            print("FAIL: expected unlock gate or live token")
            return 1
        print("OK: live mode configured")
    else:
        if not tok.get("success"):
            print("FAIL: stub token should succeed")
            return 1
        print("OK: stub mode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

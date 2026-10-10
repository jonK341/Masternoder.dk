#!/usr/bin/env python3
"""Smoke-check NFT market APIs on local or production."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://www.masternoder.dk").rstrip("/")

CHECKS = (
    "/api/nft/catalog",
    "/api/nft/deals",
    "/api/nft/listings",
    "/api/shop/paypal-items",
)


def fetch(path: str) -> dict:
    url = BASE + path
    with urllib.request.urlopen(url, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    ok = 0
    for path in CHECKS:
        try:
            data = fetch(path)
            if data.get("auto_fixed"):
                print(f"FAIL {path} still auto-stub (blueprint not loaded)")
                continue
            if path == "/api/nft/catalog":
                skus = data.get("skus") or []
                print(f"OK {path} skus={len(skus)}")
            elif path == "/api/nft/deals":
                print(
                    f"OK {path} minted={data.get('minted')} open={data.get('open_count')} "
                    f"primary_usd={data.get('primary_volume_usd')}"
                )
            elif path == "/api/shop/paypal-items":
                items = data.get("paypal_items") or {}
                nft = [k for k in items if str(k).startswith("nft-")]
                print(f"OK {path} nft_skus={len(nft)}")
            else:
                print(f"OK {path} count={data.get('count', len(data.get('listings') or []))}")
            ok += 1
        except urllib.error.HTTPError as exc:
            print(f"FAIL {path} HTTP {exc.code}")
        except Exception as exc:
            print(f"FAIL {path} {exc}")
    html_url = BASE + "/market"
    try:
        with urllib.request.urlopen(html_url, timeout=25) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        if "nft-market-panel" in body and "nft-market.js" in body:
            print(f"OK {html_url} NFT panel present")
            ok += 1
        else:
            print(f"FAIL {html_url} missing NFT panel assets")
    except Exception as exc:
        print(f"FAIL {html_url} {exc}")
    print(f"\n{ok}/{len(CHECKS) + 1} checks passed")
    return 0 if ok == len(CHECKS) + 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())

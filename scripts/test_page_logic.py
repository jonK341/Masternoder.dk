#!/usr/bin/env python3
"""
Test page logic — hit key API endpoints used by each page.
All tests must pass. Uses longer timeout + sequential + retry for reliability.
"""
import urllib.request
import json
import time

BASE = "https://masternoder.dk/vidgenerator/api"
UID = "default_user"
TIMEOUT = 45  # Allow slow endpoints (DB, aggregator)
RETRY = 2     # Retry failed requests
DELAY = 1.5   # Seconds between requests to avoid worker saturation

def test(name, path):
    url = f"{BASE}{path}" if path.startswith("/") else f"{BASE}/{path}"
    for attempt in range(RETRY + 1):
        try:
            t0 = time.perf_counter()
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                body = r.read().decode()
                elapsed = time.perf_counter() - t0
                try:
                    data = json.loads(body)
                    ok = data.get("success", True) if isinstance(data, dict) else True
                except json.JSONDecodeError:
                    ok = r.status == 200
                return r.status, elapsed, ok, (body[:80] + "..." if len(body) > 80 else body)
        except urllib.error.HTTPError as e:
            if attempt < RETRY:
                time.sleep(DELAY)
                continue
            return e.code, time.perf_counter() - t0, False, str(e)
        except Exception as e:
            if attempt < RETRY:
                time.sleep(DELAY)
                continue
            return None, time.perf_counter() - t0, False, str(e)[:80]

PAGE_APIS = [
    ("Dashboard", [
        f"/aggregator/unified-dashboard/data?user_id={UID}",
        f"/points/all?user_id={UID}",
        f"/ultra-resource/energy?user_id={UID}",
        "/monetization/top50?limit=6",
        "/agents/behavior/batch?agent_ids=agent_001,agent_002",
    ]),
    ("Profile", [
        f"/agents/my-agents?user_id={UID}",
        f"/agents/activity-feed?user_id={UID}&limit=5",
        f"/game/achievements?user_id={UID}",
        f"/battle/pvp/trophies?user_id={UID}",
        f"/trophies/list?user_id={UID}",
    ]),
    ("Stats", [
        f"/stats/aggregated?user_id={UID}&days=30",
        f"/game/achievements?user_id={UID}",
        f"/game/milestones?user_id={UID}",
        "/categories/list",
    ]),
    ("Battle", [
        f"/points/all?user_id={UID}",
        f"/battle/stats?user_id={UID}",
        f"/aggregator/frontend?user_id={UID}",
    ]),
    ("Shop", [
        f"/game/shop/currency?user_id={UID}",
        "/game/shop/items",
        f"/shop/inventory?user_id={UID}",
    ]),
    ("Trophies", [
        f"/game/achievements?user_id={UID}",
        f"/battle/pvp/trophies?user_id={UID}",
        f"/trophies/list?user_id={UID}",
    ]),
]

def main():
    print("=" * 70)
    print("PAGE LOGIC API TESTS (timeout=%ss, retry=%s)" % (TIMEOUT, RETRY))
    print("=" * 70)
    results = []
    for page, apis in PAGE_APIS:
        print(f"\n--- {page} ---")
        for path in apis:
            name = path.split("?")[0].rstrip("/").split("/")[-1] or "api"
            status, elapsed, ok, msg = test(name, path)
            s = "OK" if status == 200 and ok else "FAIL"
            t = f"{elapsed:.2f}s"
            print(f"  {name}: HTTP {status or '-'} {t} [{s}]")
            results.append((page, name, status, elapsed, ok))
            time.sleep(DELAY)  # Avoid saturating workers
    print("\n" + "=" * 70)
    ok_count = sum(1 for r in results if r[2] == 200 and r[4])
    total = len(results)
    print(f"PASS: {ok_count}/{total}")
    if ok_count < total:
        print("FAILED:", [r[1] for r in results if r[2] != 200 or not r[4]])
    print("=" * 70)
    return 0 if ok_count == total else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())

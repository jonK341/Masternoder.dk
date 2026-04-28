#!/usr/bin/env python3
"""
Hard test: time all URLs used by the front page and profile page.
Run from project root. Requires server running (or set BASE_URL to production).

  python scripts/test_url_timing.py
  BASE_URL=https://masternoder.dk python scripts/test_url_timing.py

Endpoints tested (see FRONT_PAGE_URLS and PROFILE_PAGE_URLS below):
  Front: frontpage/init, stats/summary, points/all, battle/stats, agent-skillset/all, aggregator/frontend
  Profile: user/bind-session, user/profile/<id>/aggregated, user/identity, account-summary/points,
           gallery/recent-temp, game/hunters/geo-ref, shop/paypal/control-panel, agents/activity-feed,
           agents/my-agents, trophies/list, game/achievements, battle/pvp/trophies
Output: logs/url_timing_results.json, logs/production_404_deploy_checklist.txt (if 404s). See docs/CHECKPOINTS_RECHECK.md.
"""
import os
import sys
import time
import json

try:
    import requests
except ImportError:
    print("Install: pip install requests")
    sys.exit(1)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = os.environ.get("BASE_URL", "https://masternoder.dk").rstrip("/")
# Paths below start with /vidgenerator/api/...; avoid double /vidgenerator if BASE_URL already has it
if BASE_URL.rstrip("/").endswith("/vidgenerator"):
    BASE_URL = BASE_URL.rstrip("/").rsplit("/vidgenerator", 1)[0]
USER_ID = os.environ.get("USER_ID", "default_user")
CONNECT_TIMEOUT = 5   # fail fast if server is down
# Use shorter read timeout for production so the test fails fast; override with READ_TIMEOUT env
_read = os.environ.get("READ_TIMEOUT")
READ_TIMEOUT = int(_read) if (_read and _read.isdigit()) else (15 if "masternoder.dk" in BASE_URL else 60)
TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)

# URLs used by front page (vidgenerator/index.html)
FRONT_PAGE_URLS = [
    ("/vidgenerator/api/frontpage/init", "GET", "Front page init"),
    ("/vidgenerator/api/stats/summary", "GET", "Stats summary"),
    ("/vidgenerator/api/points/all", "GET", "Points all", {"user_id": USER_ID}),
    ("/vidgenerator/api/battle/stats", "GET", "Battle stats", {"user_id": USER_ID}),
    ("/vidgenerator/api/agent-skillset/all", "GET", "Agent skillset all"),
    ("/vidgenerator/api/aggregator/frontend", "GET", "Aggregator frontend", {"user_id": USER_ID}),
]

# URLs used by profile page (vidgenerator/profile/index.html)
# POST body for bind-session is JSON { user_id: ... }
PROFILE_PAGE_URLS = [
    ("/vidgenerator/api/user/bind-session", "POST", "Bind session", {"_body": {"user_id": USER_ID}}),
    ("/vidgenerator/api/user/profile/" + USER_ID + "/aggregated", "GET", "Profile aggregated"),
    ("/vidgenerator/api/user/identity", "GET", "User identity", {"user_id": USER_ID}),
    ("/vidgenerator/api/user/account-summary/points", "GET", "Account summary points", {"user_id": USER_ID}),
    ("/vidgenerator/api/gallery/recent-temp", "GET", "Gallery recent"),
    ("/vidgenerator/api/game/hunters/geo-ref", "GET", "Geo ref", {"user_id": USER_ID}),
    ("/vidgenerator/api/shop/paypal/control-panel", "GET", "PayPal control panel", {"user_id": USER_ID}),
    ("/vidgenerator/api/agents/activity-feed", "GET", "Agents activity feed", {"user_id": USER_ID, "limit": "20"}),
    ("/vidgenerator/api/agents/my-agents", "GET", "My agents", {"user_id": USER_ID}),
    ("/vidgenerator/api/trophies/list", "GET", "Trophies list", {"user_id": USER_ID}),
    ("/vidgenerator/api/game/achievements", "GET", "Game achievements", {"user_id": USER_ID}),
    ("/vidgenerator/api/battle/pvp/trophies", "GET", "Battle PVP trophies", {"user_id": USER_ID}),
]


def time_request(path: str, method: str, name: str, params: dict = None) -> dict:
    url = BASE_URL + path
    body = None
    query = dict(params) if params else {}
    if "_body" in query:
        body = query.pop("_body")
    if query and "?" not in path:
        q = "&".join(f"{k}={v}" for k, v in query.items())
        url = url + ("?" + q)
    start = time.perf_counter()
    try:
        if method == "GET":
            r = requests.get(url, timeout=TIMEOUT, headers={"Accept": "application/json"})
        else:
            r = requests.post(
                url, timeout=TIMEOUT, json=body or {}, headers={"Content-Type": "application/json"}
            )
        elapsed = time.perf_counter() - start
        status = r.status_code
        ok = 200 <= status < 300
        return {
            "name": name,
            "path": path,
            "method": method,
            "status": status,
            "ok": ok,
            "elapsed_sec": round(elapsed, 2),
            "error": None,
        }
    except requests.exceptions.ConnectionError:
        elapsed = time.perf_counter() - start
        return {
            "name": name,
            "path": path,
            "method": method,
            "status": None,
            "ok": False,
            "elapsed_sec": round(elapsed, 2),
            "error": "Connection refused",
        }
    except requests.exceptions.Timeout:
        elapsed = time.perf_counter() - start
        return {
            "name": name,
            "path": path,
            "method": method,
            "status": None,
            "ok": False,
            "elapsed_sec": round(elapsed, 2),
            "error": "Timeout",
        }
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "name": name,
            "path": path,
            "method": method,
            "status": None,
            "ok": False,
            "elapsed_sec": round(elapsed, 2),
            "error": str(e),
        }


def main():
    print("=" * 70)
    print("URL timing test – front page & profile page")
    print("BASE_URL:", BASE_URL)
    print("USER_ID:", USER_ID)
    print("Timeout: connect %ss, read %ss" % (CONNECT_TIMEOUT, READ_TIMEOUT))
    print("=" * 70)

    all_results = []
    for item in FRONT_PAGE_URLS:
        if len(item) == 4:
            path, method, name, params = item
        else:
            path, method, name = item
            params = None
        res = time_request(path, method, name, params)
        all_results.append(res)
        sym = "OK" if res["ok"] else "FAIL"
        err = f"  # {res['error']}" if res.get("error") else ""
        print(f"  [{sym}] {res['elapsed_sec']:>6.2f}s  {res['status'] or '—':>4}  {name}{err}")

    print()
    print("--- Profile page URLs ---")
    for item in PROFILE_PAGE_URLS:
        if len(item) == 4:
            path, method, name, params = item
        else:
            path, method, name = item
            params = None
        res = time_request(path, method, name, params)
        all_results.append(res)
        sym = "OK" if res["ok"] else "FAIL"
        err = f"  # {res['error']}" if res.get("error") else ""
        print(f"  [{sym}] {res['elapsed_sec']:>6.2f}s  {res['status'] or '—':>4}  {name}{err}")

    total = sum(r["elapsed_sec"] for r in all_results)
    slow = [r for r in all_results if r["elapsed_sec"] >= 2.0]
    failed = [r for r in all_results if not r["ok"]]

    print()
    print("=" * 70)
    print(f"Total sequential time: {total:.1f}s  |  OK: {len(all_results) - len(failed)}  |  Failed: {len(failed)}")
    if slow:
        print("Slow (>= 2s):", ", ".join(f"{r['name']} ({r['elapsed_sec']}s)" for r in sorted(slow, key=lambda x: -x["elapsed_sec"])))
    if failed:
        print("Failed:", ", ".join(r["name"] for r in failed))
    if failed and all(r.get("error") == "Connection refused" for r in failed):
        print("\n  Server not running? Start Flask, or test production: set BASE_URL=https://masternoder.dk")
    print("=" * 70)

    out_file = os.path.join(BASE, "logs", "url_timing_results.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(
            {"base_url": BASE_URL, "user_id": USER_ID, "results": all_results, "total_sec": total},
            f,
            indent=2,
        )
    print("Results saved to:", out_file)

    # If any 404s, write deploy checklist so production can be fixed
    four_oh_fours = [r for r in all_results if r.get("status") == 404]
    deploy_checklist = {
        "frontpage/init": "backend/routes/missing_endpoints_routes.py",
        "battle/stats": "backend/routes/battle_routes.py",
        "agent-skillset/all": "backend/routes/agent_automation_routes.py",
        "profile/aggregated": "backend/routes/user_profile_routes.py",
        "user/identity": "backend/routes/user_account_routes.py",
        "account-summary/points": "backend/routes/user_account_routes.py",
        "gallery/recent-temp": "backend/routes/gallery_routes.py",
        "trophies/list": "backend/routes/trophies_routes.py",
        "battle/pvp/trophies": "backend/routes/battle_routes.py",
    }
    if four_oh_fours:
        checklist_path = os.path.join(BASE, "logs", "production_404_deploy_checklist.txt")
        with open(checklist_path, "w", encoding="utf-8") as f:
            f.write("Production 404s – ensure these route files are deployed and blueprints registered.\n")
            f.write("Fallbacks for all listed endpoints exist in backend/routes/missing_endpoints_routes.py (deploy it first).\n\n")
            for r in four_oh_fours:
                path = r.get("path", "")
                key = next((k for k in deploy_checklist if k in path), path)
                f.write("  %s  ->  %s\n" % (r.get("name", path), deploy_checklist.get(key, "check register_blueprints.py")))
        print("404 deploy checklist:", checklist_path)

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())

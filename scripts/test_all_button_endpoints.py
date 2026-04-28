#!/usr/bin/env python3
"""
Test all button-triggered API endpoints (debugger, profile, generator, etc.).
Run from project root. Requires server running: python scripts/test_all_button_endpoints.py
Optional: BASE_URL=http://127.0.0.1:5000 (default) or https://masternoder.dk
"""
import os
import sys
import json

try:
    import requests
except ImportError:
    print("Install: pip install requests")
    sys.exit(1)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000").rstrip("/")
TIMEOUT = 15

# Endpoints used by debugger and main UI buttons (path relative to site root; we prepend BASE_URL)
ENDPOINTS = [
    # System / Mission Control
    ("/vidgenerator/api/system/overview", "GET", "Mission Control / System Overview"),
    ("/vidgenerator/api/system/overview?compact=1", "GET", "System Overview (compact)"),
    ("/api/ai/providers", "GET", "AI Providers status"),
    ("/vidgenerator/api/ai/video-providers", "GET", "Video/AI providers"),
    # Debug
    ("/vidgenerator/api/debug/all-systems", "GET", "Debug All Systems"),
    ("/vidgenerator/api/debug/all-routes", "GET", "Debug All Routes"),
    ("/vidgenerator/api/debug/check-duplicates", "GET", "Check Duplicates"),
    ("/vidgenerator/api/debug/report", "GET", "Generate Report"),
    # Scanner
    ("/vidgenerator/api/debugger/scanner/scan", "GET", "Scanner Scan All"),
    ("/vidgenerator/api/debugger/scanner/blueprints", "GET", "Scanner Blueprints"),
    ("/vidgenerator/api/debugger/scanner/routes", "GET", "Scanner Routes"),
    ("/vidgenerator/api/debugger/scanner/missing", "GET", "Scanner Missing"),
    ("/vidgenerator/api/debugger/scanner/suggestions", "GET", "Scanner Suggestions"),
    # Agent fix (POST)
    ("/vidgenerator/api/debugger/agent/fix-personality", "POST", "Fix Personality"),
    ("/vidgenerator/api/debugger/agent/fix-missions", "POST", "Fix Missions"),
    ("/vidgenerator/api/debugger/agent/fix-quests", "POST", "Fix Quests"),
    ("/vidgenerator/api/debugger/agent/fix-history", "POST", "Fix History"),
    ("/vidgenerator/api/debugger/agent/fix-behavior", "POST", "Fix Behavior"),
    ("/vidgenerator/api/debugger/agent/fix-all", "POST", "Fix All"),
    # Agent get
    ("/vidgenerator/api/agent/master-fix/personality", "GET", "Get Personality"),
    ("/vidgenerator/api/agent/master-fix/missions", "GET", "Get Missions"),
    ("/vidgenerator/api/agent/master-fix/quests", "GET", "Get Quests"),
    ("/vidgenerator/api/agent/master-fix/history", "GET", "Get History"),
    ("/vidgenerator/api/agent/master-fix/statistics", "GET", "Get Statistics"),
    ("/vidgenerator/api/agent/master-fix/behavior-pattern", "GET", "Get Behavior"),
    ("/vidgenerator/api/agent/master-fix/run-full-diagnostic", "POST", "Run Diagnostic"),
    # Profile / debugger profile
    ("/vidgenerator/api/debugger/profile/points", "GET", "Profile Points", {"user_id": "default_user"}),
    ("/vidgenerator/api/debugger/profile/stats", "GET", "Profile Stats", {"user_id": "default_user"}),
    ("/vidgenerator/api/debugger/profile/agent-points", "GET", "Agent Points", {"agent_id": "agent_manager"}),
    ("/vidgenerator/api/user/profile/default_user/aggregated", "GET", "Profile Aggregated"),
    # Tasks
    ("/vidgenerator/api/debugger/tasks/list", "GET", "List Tasks"),
    ("/vidgenerator/api/debugger/tasks/stats", "GET", "Task Stats"),
    ("/vidgenerator/api/errors/tasks/list", "GET", "Error Tasks List"),
    ("/vidgenerator/api/errors/tasks/stats", "GET", "Error Tasks Stats"),
    # Errors
    ("/vidgenerator/api/errors/stats", "GET", "Error Stats", {"days": "7"}),
    ("/vidgenerator/api/errors/list", "GET", "Error List", {"limit": "10"}),
    ("/vidgenerator/api/errors/handler-status/analyze", "GET", "Error Handler Status"),
    # Sync / points (profile, generator)
    ("/vidgenerator/api/sync/status", "GET", "Sync Status"),
    ("/vidgenerator/api/points/all", "GET", "Points All", {"user_id": "default_user"}),
    ("/vidgenerator/api/points/comprehensive", "GET", "Points Comprehensive", {"user_id": "default_user"}),
    # Quests / shop / leaderboard (buttons in Mission Control)
    ("/vidgenerator/api/quests/daily", "GET", "Quests Daily"),
    ("/vidgenerator/api/leaderboard/ai-insights", "GET", "Leaderboard AI Insights"),
    ("/vidgenerator/api/shop/daily-deal", "GET", "Shop Daily Deal"),
    # Generator (no POST here to avoid creating jobs)
    ("/vidgenerator/api/unified/status", "GET", "Unified Generator Status"),
]


def test_endpoint(path: str, method: str, name: str, params: dict = None) -> dict:
    url = BASE_URL + path
    if params and method == "GET" and "?" not in path:
        q = "&".join(f"{k}={v}" for k, v in params.items())
        url = url + ("?" + q)
    try:
        if method == "GET":
            r = requests.get(url, timeout=TIMEOUT, headers={"Accept": "application/json"})
        else:
            r = requests.post(url, timeout=TIMEOUT, json=params or {}, headers={"Content-Type": "application/json"})
        status = r.status_code
        ok = 200 <= status < 300
        return {"name": name, "path": path, "method": method, "status": status, "ok": ok, "error": None}
    except requests.exceptions.ConnectionError as e:
        return {"name": name, "path": path, "method": method, "status": None, "ok": False, "error": "Connection refused (server down?)"}
    except requests.exceptions.Timeout:
        return {"name": name, "path": path, "method": method, "status": None, "ok": False, "error": "Timeout"}
    except Exception as e:
        return {"name": name, "path": path, "method": method, "status": None, "ok": False, "error": str(e)}


def main():
    print("=" * 60)
    print("Button / API endpoint test")
    print("BASE_URL:", BASE_URL)
    print("=" * 60)

    results = []
    for item in ENDPOINTS:
        if len(item) == 4:
            path, method, name, params = item
        else:
            path, method, name = item
            params = None
        res = test_endpoint(path, method, name, params)
        results.append(res)
        status_str = str(res["status"]) if res["status"] else "ERR"
        symbol = "OK" if res["ok"] else "FAIL"
        err = f"  # {res['error']}" if res.get("error") else ""
        print(f"  [{symbol}] {status_str:>6}  {method:4}  {name}{err}")

    ok_count = sum(1 for r in results if r["ok"])
    fail_count = len(results) - ok_count
    four_oh_four = [r for r in results if r.get("status") == 404]
    five_hundred = [r for r in results if r.get("status") == 500]

    print()
    print("=" * 60)
    print(f"Total: {len(results)}  |  OK: {ok_count}  |  Failed: {fail_count}")
    if four_oh_four:
        print(f"404 ({len(four_oh_four)}):", ", ".join(r["name"] for r in four_oh_four))
    if five_hundred:
        print(f"500 ({len(five_hundred)}):", ", ".join(r["name"] for r in five_hundred))
    conn_refused = [r for r in results if "Connection refused" in str(r.get("error") or "")]
    if conn_refused:
        print("Connection refused (server not running?) for all. Start Flask then re-run.")
    print("=" * 60)

    out_file = os.path.join(BASE, "logs", "button_endpoint_test_results.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"base_url": BASE_URL, "results": results, "ok": ok_count, "failed": fail_count}, f, indent=2)
    print("Results saved to:", out_file)

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

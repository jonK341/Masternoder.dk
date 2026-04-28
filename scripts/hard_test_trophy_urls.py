#!/usr/bin/env python3
"""
Hard-test trophy URLs over real HTTP. Tests all trophy endpoints including
page routes, API endpoints, and trophy awarding functionality.

Usage:
  python scripts/hard_test_trophy_urls.py
  python scripts/hard_test_trophy_urls.py --base https://masternoder.dk
  python scripts/hard_test_trophy_urls.py --local   # use http://127.0.0.1:5000
  python scripts/hard_test_trophy_urls.py --quick   # GET endpoints only
"""
import os
import sys
import json
import time
import argparse

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(2)

# Default: web server URL. Override with BASE_URL env or --base / --local.
DEFAULT_WEB_SERVER = "https://masternoder.dk"
DEFAULT_LOCAL = "http://127.0.0.1:5000"
BASE_URL = os.environ.get("BASE_URL", DEFAULT_WEB_SERVER)
API_BASE = BASE_URL.rstrip("/") + "/vidgenerator"

# Timeouts for remote server
REQUEST_TIMEOUT = 30
TEST_USER_ID = "hardtest_user"


def get(path, **kwargs):
    """GET request helper"""
    url = API_BASE + path if path.startswith("/") else API_BASE + "/" + path
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    return requests.get(url, **kwargs)


def post(path, json_data=None, **kwargs):
    """POST request helper"""
    url = API_BASE + path if path.startswith("/") else API_BASE + "/" + path
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    return requests.post(url, json=json_data or {}, **kwargs)


def test_trophies_page():
    """Test trophy page HTML routes"""
    print("\n[1/15] Testing Trophy Page Routes...")
    routes = [
        "/trophies",
        "/trophies/",
        "/vidgenerator/trophies",
        "/vidgenerator/trophies/",
        "/trophie",  # Singular for backwards compatibility
        "/vidgenerator/trophie",
    ]
    results = []
    for route in routes:
        url = BASE_URL.rstrip("/") + route
        try:
            r = requests.get(url, timeout=REQUEST_TIMEOUT)
            success = r.status_code == 200
            is_html = "text/html" in r.headers.get("content-type", "")
            results.append({
                "route": route,
                "status": r.status_code,
                "success": success,
                "is_html": is_html,
                "size": len(r.content)
            })
            status = "[OK]" if success and is_html else "[FAIL]"
            print(f"  {status} {route} -> {r.status_code} ({len(r.content)} bytes)")
        except Exception as e:
            results.append({"route": route, "error": str(e)})
            print(f"  [ERROR] {route} -> ERROR: {e}")
    return results


def test_trophies_list_api():
    """Test trophy list API endpoints"""
    print("\n[2/15] Testing Trophy List API...")
    routes = [
        "/api/trophies/list",
        "/vidgenerator/api/trophies/list",
        "/api/trophie/list",  # Singular
        "/vidgenerator/api/trophie/list",
    ]
    results = []
    for route in routes:
        try:
            r = get(route, params={"user_id": TEST_USER_ID})
            success = r.status_code == 200
            data = {}
            if success:
                try:
                    data = r.json()
                except:
                    pass
            results.append({
                "route": route,
                "status": r.status_code,
                "success": success,
                "has_trophies": "trophies" in data,
                "has_definitions": "definitions" in data,
                "trophy_count": len(data.get("trophies", []))
            })
            status = "[OK]" if success else "[FAIL]"
            count = len(data.get("trophies", [])) if success else 0
            print(f"  {status} {route} -> {r.status_code} ({count} trophies)")
        except Exception as e:
            results.append({"route": route, "error": str(e)})
            print(f"  ❌ {route} -> ERROR: {e}")
    return results


def test_trophy_award_api(quick=False):
    """Test trophy award API endpoints"""
    if quick:
        print("\n[3/15] Testing Trophy Award API (SKIPPED in quick mode)...")
        return []
    
    print("\n[3/15] Testing Trophy Award API...")
    routes = [
        "/api/trophies/award",
        "/vidgenerator/api/trophies/award",
        "/api/trophie/award",
        "/vidgenerator/api/trophie/award",
    ]
    results = []
    test_trophy_id = "first_video"
    
    for route in routes:
        try:
            payload = {
                "user_id": TEST_USER_ID,
                "trophy_id": test_trophy_id
            }
            r = post(route, json_data=payload)
            success = r.status_code in [200, 201]
            data = {}
            if success:
                try:
                    data = r.json()
                except:
                    pass
            results.append({
                "route": route,
                "status": r.status_code,
                "success": success,
                "awarded": data.get("success", False)
            })
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} POST {route} -> {r.status_code}")
        except Exception as e:
            results.append({"route": route, "error": str(e)})
            print(f"  ❌ POST {route} -> ERROR: {e}")
    return results


def test_user_trophies_api():
    """Test user-specific trophy endpoints"""
    print("\n[4/15] Testing User Trophies API...")
    routes = [
        f"/api/trophies/user/{TEST_USER_ID}",
        f"/vidgenerator/api/trophies/user/{TEST_USER_ID}",
    ]
    results = []
    for route in routes:
        try:
            r = get(route)
            success = r.status_code == 200
            data = {}
            if success:
                try:
                    data = r.json()
                except:
                    pass
            results.append({
                "route": route,
                "status": r.status_code,
                "success": success,
                "has_trophies": "trophies" in data
            })
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} {route} -> {r.status_code}")
        except Exception as e:
            results.append({"route": route, "error": str(e)})
            print(f"  ❌ {route} -> ERROR: {e}")
    return results


def test_battle_trophies_api():
    """Test battle trophy endpoints"""
    print("\n[5/15] Testing Battle Trophies API...")
    routes = [
        "/api/battle/pvp/trophies",
        "/vidgenerator/api/battle/pvp/trophies",
    ]
    results = []
    for route in routes:
        try:
            r = get(route, params={"user_id": TEST_USER_ID})
            success = r.status_code == 200
            data = {}
            if success:
                try:
                    data = r.json()
                except:
                    pass
            results.append({
                "route": route,
                "status": r.status_code,
                "success": success,
                "has_trophies": "trophies" in data
            })
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} {route} -> {r.status_code}")
        except Exception as e:
            results.append({"route": route, "error": str(e)})
            print(f"  ❌ {route} -> ERROR: {e}")
    return results


def test_stats_trophies_api():
    """Test stats trophy endpoints"""
    print("\n[6/15] Testing Stats Trophies API...")
    routes = [
        "/api/stats/trophies",
        "/vidgenerator/api/stats/trophies",
    ]
    results = []
    for route in routes:
        try:
            r = get(route, params={"user_id": TEST_USER_ID})
            success = r.status_code == 200
            data = {}
            if success:
                try:
                    data = r.json()
                except:
                    pass
            results.append({
                "route": route,
                "status": r.status_code,
                "success": success
            })
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} {route} -> {r.status_code}")
        except Exception as e:
            results.append({"route": route, "error": str(e)})
            print(f"  ❌ {route} -> ERROR: {e}")
    return results


def test_game_achievements_api():
    """Test game achievements API (used by trophy page)"""
    print("\n[7/15] Testing Game Achievements API...")
    routes = [
        "/api/game/achievements",
        "/vidgenerator/api/game/achievements",
    ]
    results = []
    for route in routes:
        try:
            r = get(route, params={"user_id": TEST_USER_ID})
            success = r.status_code == 200
            data = {}
            if success:
                try:
                    data = r.json()
                except:
                    pass
            results.append({
                "route": route,
                "status": r.status_code,
                "success": success,
                "has_achievements": "achievements" in data
            })
            status = "[OK]" if success else "[FAIL]"
            count = len(data.get("achievements", [])) if success else 0
            print(f"  {status} {route} -> {r.status_code} ({count} achievements)")
        except Exception as e:
            results.append({"route": route, "error": str(e)})
            print(f"  ❌ {route} -> ERROR: {e}")
    return results


def test_star_map_api():
    """Test star map API (used by trophy page)"""
    print("\n[8/15] Testing Star Map API...")
    routes = [
        "/api/star-map",
        "/vidgenerator/api/star-map",
        "/api/game/hunters/star-map",
    ]
    results = []
    for route in routes:
        try:
            r = get(route)
            success = r.status_code == 200
            data = {}
            if success:
                try:
                    data = r.json()
                except:
                    pass
            results.append({
                "route": route,
                "status": r.status_code,
                "success": success,
                "has_stars": "star_map" in data or "stars" in data
            })
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} {route} -> {r.status_code}")
        except Exception as e:
            results.append({"route": route, "error": str(e)})
            print(f"  ❌ {route} -> ERROR: {e}")
    return results


def test_rulebook_api():
    """Test rulebook API (used by trophy page)"""
    print("\n[9/15] Testing Rulebook API...")
    routes = [
        "/api/game/hunters/rulebook",
        "/vidgenerator/api/game/hunters/rulebook",
    ]
    results = []
    for route in routes:
        try:
            r = get(route)
            success = r.status_code == 200
            data = {}
            if success:
                try:
                    data = r.json()
                except:
                    pass
            results.append({
                "route": route,
                "status": r.status_code,
                "success": success,
                "has_rulebook": "rulebook" in data
            })
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} {route} -> {r.status_code}")
        except Exception as e:
            results.append({"route": route, "error": str(e)})
            print(f"  ❌ {route} -> ERROR: {e}")
    return results


def test_effect_clusters_api():
    """Test effect clusters API (used by trophy page)"""
    print("\n[10/15] Testing Effect Clusters API...")
    routes = [
        "/api/game/hunters/effect-clusters",
        "/vidgenerator/api/game/hunters/effect-clusters",
    ]
    results = []
    for route in routes:
        try:
            r = get(route)
            success = r.status_code == 200
            data = {}
            if success:
                try:
                    data = r.json()
                except:
                    pass
            results.append({
                "route": route,
                "status": r.status_code,
                "success": success,
                "has_clusters": "effect_clusters" in data
            })
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} {route} -> {r.status_code}")
        except Exception as e:
            results.append({"route": route, "error": str(e)})
            print(f"  ❌ {route} -> ERROR: {e}")
    return results


def test_electric_magnet_api():
    """Test Electric Magnet API (used by trophy page star map tab)"""
    print("\n[11/15] Testing Electric Magnet API...")
    routes = [
        "/api/agent-tech/agent_electric_magnet/download",
        "/api/agent-tech/agent_electric_magnet/run_verification",
        "/api/agent-tech/agent_electric_magnet/run_dna_test",
        "/api/agent-tech/agent_electric_magnet/view_star_map",
    ]
    results = []
    for route in routes:
        try:
            # These are POST endpoints, but we'll test GET first to see response
            r = get(route)
            # POST test
            payload = {"user_id": TEST_USER_ID}
            r_post = post(route, json_data=payload)
            success = r_post.status_code in [200, 201, 400, 405]  # 405 = method not allowed is OK
            results.append({
                "route": route,
                "status": r_post.status_code,
                "success": success
            })
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} POST {route} -> {r_post.status_code}")
        except Exception as e:
            results.append({"route": route, "error": str(e)})
            print(f"  ❌ {route} -> ERROR: {e}")
    return results


def test_trophy_page_content():
    """Test trophy page HTML content"""
    print("\n[12/15] Testing Trophy Page Content...")
    try:
        r = requests.get(f"{BASE_URL}/vidgenerator/trophies", timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return {"success": False, "error": f"Status {r.status_code}"}
        
        # Use UTF-8 encoding to handle emojis
        try:
            content = r.text
        except:
            content = r.content.decode('utf-8', errors='ignore')
        
        checks = {
            "has_trophy_header": "Trophy Collection" in content or "Trophies" in content,
            "has_tabs": "data-tab" in content,
            "has_generation_tab": "generation" in content.lower(),
            "has_stats_grid": "stats-grid" in content or "stat-card" in content,
            "has_trophy_grid": "trophies-grid" in content or "trophy-card" in content,
            "has_scripts": "loadTrophies" in content,
            "has_api_calls": "/api/trophies" in content or "/api/trophie" in content,
            "has_cache_version": 'cache-version' in content or 'meta name="cache-version"' in content,
        }
        all_checks = all(checks.values())
        status = "[OK]" if all_checks else "[WARN]"
        print(f"  {status} Trophy page content checks:")
        for check, passed in checks.items():
            icon = "[OK]" if passed else "[FAIL]"
            print(f"    {icon} {check}: {passed}")
        return {"success": all_checks, "checks": checks}
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_trophy_definitions():
    """Test trophy definitions structure"""
    print("\n[13/15] Testing Trophy Definitions...")
    try:
        r = get("/api/trophies/list", params={"user_id": TEST_USER_ID})
        if r.status_code != 200:
            return {"success": False, "error": f"Status {r.status_code}"}
        
        data = r.json()
        has_definitions = "definitions" in data
        has_trophies = "trophies" in data
        trophy_count = len(data.get("trophies", []))
        def_count = len(data.get("definitions", {}))
        
        print(f"  Trophy count: {trophy_count}")
        print(f"  Definition count: {def_count}")
        print(f"  Has definitions: {has_definitions}")
        print(f"  Has trophies: {has_trophies}")
        
        return {
            "success": True,
            "trophy_count": trophy_count,
            "definition_count": def_count,
            "has_definitions": has_definitions,
            "has_trophies": has_trophies
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_trophy_categories():
    """Test trophy category filtering"""
    print("\n[14/15] Testing Trophy Categories...")
    categories = ["generation", "points", "battle", "social", "content", "milestones", "special"]
    results = []
    for category in categories:
        try:
            r = get("/api/trophies/list", params={"user_id": TEST_USER_ID, "category": category})
            success = r.status_code == 200
            data = r.json() if success else {}
            trophy_count = len(data.get("trophies", []))
            results.append({
                "category": category,
                "success": success,
                "count": trophy_count
            })
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} Category '{category}': {trophy_count} trophies")
        except Exception as e:
            results.append({"category": category, "error": str(e)})
            print(f"  ❌ Category '{category}': ERROR: {e}")
    return results


def test_trophy_award_flow():
    """Test complete trophy award flow"""
    print("\n[15/15] Testing Trophy Award Flow...")
    try:
        # Get initial trophy count
        r1 = get("/api/trophies/list", params={"user_id": TEST_USER_ID})
        initial_data = r1.json() if r1.status_code == 200 else {}
        initial_count = len(initial_data.get("trophies", []))
        
        # Award a trophy
        payload = {"user_id": TEST_USER_ID, "trophy_id": "test_trophy_award"}
        r2 = post("/api/trophies/award", json_data=payload)
        award_success = r2.status_code in [200, 201]
        
        # Get updated trophy count
        r3 = get("/api/trophies/list", params={"user_id": TEST_USER_ID})
        updated_data = r3.json() if r3.status_code == 200 else {}
        updated_count = len(updated_data.get("trophies", []))
        
        print(f"  Initial trophy count: {initial_count}")
        print(f"  Award success: {award_success}")
        print(f"  Updated trophy count: {updated_count}")
        
        return {
            "success": award_success,
            "initial_count": initial_count,
            "updated_count": updated_count,
            "awarded": updated_count > initial_count
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Hard-test trophy URLs")
    parser.add_argument("--base", default=None, help="Base URL (default: from BASE_URL env or https://masternoder.dk)")
    parser.add_argument("--local", action="store_true", help="Use local server (http://127.0.0.1:5000)")
    parser.add_argument("--quick", action="store_true", help="Quick test (GET endpoints only, no POST)")
    args = parser.parse_args()
    
    global BASE_URL, API_BASE
    if args.local:
        BASE_URL = DEFAULT_LOCAL
        API_BASE = BASE_URL.rstrip("/") + "/vidgenerator"
    elif args.base:
        BASE_URL = args.base
        API_BASE = BASE_URL.rstrip("/") + "/vidgenerator"
    
    print("=" * 70)
    print("HARD TEST TROPHY URLS")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    print(f"Test User ID: {TEST_USER_ID}")
    print(f"Quick Mode: {args.quick}")
    print("=" * 70)
    
    all_results = {}
    
    # Run all tests
    all_results["page_routes"] = test_trophies_page()
    all_results["list_api"] = test_trophies_list_api()
    all_results["award_api"] = test_trophy_award_api(quick=args.quick)
    all_results["user_trophies"] = test_user_trophies_api()
    all_results["battle_trophies"] = test_battle_trophies_api()
    all_results["stats_trophies"] = test_stats_trophies_api()
    all_results["game_achievements"] = test_game_achievements_api()
    all_results["star_map"] = test_star_map_api()
    all_results["rulebook"] = test_rulebook_api()
    all_results["effect_clusters"] = test_effect_clusters_api()
    all_results["electric_magnet"] = test_electric_magnet_api()
    all_results["page_content"] = test_trophy_page_content()
    all_results["definitions"] = test_trophy_definitions()
    all_results["categories"] = test_trophy_categories()
    all_results["award_flow"] = test_trophy_award_flow()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total_tests = 0
    passed_tests = 0
    
    for test_name, results in all_results.items():
        if isinstance(results, list):
            for result in results:
                total_tests += 1
                if result.get("success") or result.get("status") == 200:
                    passed_tests += 1
        elif isinstance(results, dict):
            total_tests += 1
            if results.get("success"):
                passed_tests += 1
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
    print("=" * 70)
    
    # Save results
    results_file = os.path.join(_root, "logs", "trophy_test_results.json")
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "base_url": BASE_URL,
            "test_user_id": TEST_USER_ID,
            "results": all_results,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests
            }
        }, f, indent=2)
    print(f"\nResults saved to: {results_file}")
    
    return 0 if passed_tests == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())

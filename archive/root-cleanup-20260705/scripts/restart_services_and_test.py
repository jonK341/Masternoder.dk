"""
Restart Services and Test Endpoints
Can be run locally to test or on server to restart
"""
import subprocess
import time
import requests
import sys

BASE_URL = "https://masternoder.dk"
TEST_USER = "test_user"

def test_endpoint(endpoint, description):
    """Test an endpoint"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n[TEST] {description}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=10, verify=True)
        if response.status_code == 200:
            print(f"[OK] Status: {response.status_code}")
            try:
                data = response.json()
                print(f"[OK] Response: {str(data)[:200]}...")
                return True
            except:
                print(f"[OK] Response: {response.text[:200]}...")
                return True
        else:
            print(f"[WARN] Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

def main():
    """Main test function"""
    print("="*60)
    print("RESTART SERVICES AND TEST ENDPOINTS")
    print("="*60)
    print("\n[INFO] This script tests endpoints after services restart")
    print("[INFO] Make sure services are restarted on server first!")
    print("\n" + "="*60)
    
    # Wait a bit for services to be ready
    print("\n[INFO] Waiting 5 seconds for services to be ready...")
    time.sleep(5)
    
    # Test endpoints
    endpoints = [
        ("/vidgenerator/api/ultra-resource/energy", "Ultra Resource Controller - Energy"),
        ("/vidgenerator/api/game-mechanics/subjects", "Game Mechanics - Subjects"),
        ("/vidgenerator/api/skill-reward/completions", "Skill Rewards - Completions"),
        ("/vidgenerator/api/calendar/events", "Calendar Planner - Events"),
        ("/vidgenerator/api/todos/list", "Todos - List"),
        ("/vidgenerator/api/decision-trees/tech", "Decision Trees - Tech"),
        ("/vidgenerator/api/groups/user", "Groups - User Groups"),
        ("/vidgenerator/api/scanner/efficiency", "Cognitive Scanner - Efficiency"),
        ("/vidgenerator/api/skills/abilities", "Enhanced Skills - Abilities"),
        ("/vidgenerator/api/points/json/get", "Points JSON - Get Points"),
    ]
    
    results = []
    for endpoint, description in endpoints:
        full_endpoint = f"{endpoint}?user_id={TEST_USER}" if "?" not in endpoint else f"{endpoint}&user_id={TEST_USER}"
        result = test_endpoint(full_endpoint, description)
        results.append((description, result))
        time.sleep(1)  # Small delay between requests
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for description, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {description}")
    
    print(f"\n[RESULT] {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All endpoints working!")
        return 0
    else:
        print("[WARNING] Some endpoints failed. Check server logs.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[WARN] Testing cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Testing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


#!/usr/bin/env python3
"""
Test API Endpoints One by One - Detailed testing
"""
import requests
import sys
import time

BASE_URL = "https://masternoder.dk"

ENDPOINTS = [
    # Agent Controller
    ("Agent Controller Status", "/vidgenerator/api/agent-controller/status"),
    ("Agent Controller Status (Alt)", "/vidgenerator/api/agents/controller/status"),
    ("Agent Controller All Agents", "/vidgenerator/api/agent-controller/all-agents"),
    ("Agent Controller All Agents (Alt)", "/vidgenerator/api/agents/controller/all-agents"),
    
    # Agent Skillsets
    ("Agent Skillset Stats", "/vidgenerator/api/agent/skillset/stats"),
    ("Agent Skillset Stats (Alt)", "/vidgenerator/api/agents/skillsets/stats"),
    ("Agent Skillset All", "/vidgenerator/api/agent/skillset/all"),
    ("Agent Skillset All (Alt)", "/vidgenerator/api/agents/skillsets/all"),
    
    # Agent Automation (should work)
    ("Agent Automation Status", "/vidgenerator/api/agent/automation/status"),
    
    # User Agent Skills (should work)
    ("User Agent Skills", "/vidgenerator/api/user/agent-skills/test_user_1"),
    ("User Scraped Info", "/vidgenerator/api/user/scraped-info/test_user_1"),
]

def test_endpoint(name, endpoint):
    """Test a single endpoint with detailed output"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*70}")
    
    try:
        response = requests.get(url, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ SUCCESS - JSON Response:")
                print(f"   Keys: {list(data.keys())}")
                if 'success' in data:
                    print(f"   Success: {data['success']}")
                if 'error' in data:
                    print(f"   Error: {data['error']}")
                # Print first 200 chars of response
                import json
                print(f"   Response preview: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(f"✅ SUCCESS - Non-JSON Response:")
                print(f"   Length: {len(response.text)} bytes")
                print(f"   Preview: {response.text[:200]}...")
            return True
        else:
            print(f"❌ FAILED - Status {response.status_code}")
            print(f"   Response preview: {response.text[:300]}...")
            
            # Check if it's an HTML 404 page
            if '404' in response.text or '<title>404' in response.text:
                print(f"   ⚠️  This is an HTML 404 page (route not found)")
            
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT - Request timed out after 10 seconds")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ CONNECTION ERROR - {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR - {type(e).__name__}: {e}")
        return False

def main():
    """Test all endpoints one by one"""
    print("=" * 70)
    print("API Endpoint Testing - One by One")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print(f"Total Endpoints: {len(ENDPOINTS)}")
    print()
    
    results = []
    
    for name, endpoint in ENDPOINTS:
        success = test_endpoint(name, endpoint)
        results.append((name, endpoint, success))
        time.sleep(0.5)  # Small delay between requests
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    success_count = sum(1 for _, _, s in results if s)
    total_count = len(results)
    
    print(f"\n✅ Working: {success_count}/{total_count}")
    for name, endpoint, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    print(f"\n❌ Failing: {total_count - success_count}/{total_count}")
    for name, endpoint, success in results:
        if not success:
            print(f"   - {name}: {endpoint}")
    
    print()
    
    return 0 if success_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())

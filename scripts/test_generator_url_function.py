#!/usr/bin/env python3
"""
Test Generator URL and Function - Comprehensive Test
Tests all generator endpoints and identifies reusable patterns
"""
import sys
import requests
import json
import time

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'https://masternoder.dk/vidgenerator'

def test_generator_urls():
    """Test all generator-related URLs"""
    print("="*80)
    print("GENERATOR URL & FUNCTION TEST")
    print("="*80)
    
    results = {}
    
    # Test 1: Generator Page
    print("\n[TEST 1] Generator Page")
    try:
        response = requests.get(f"{BASE_URL}/generator", timeout=10)
        results['generator_page'] = response.status_code == 200
        print(f"  Status: {response.status_code} {'✅' if results['generator_page'] else '❌'}")
    except Exception as e:
        results['generator_page'] = False
        print(f"  ❌ Error: {e}")
    
    # Test 2: Health Check
    print("\n[TEST 2] Health Check Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/api/generator/test", timeout=10)
        data = response.json() if response.status_code == 200 else None
        results['health_check'] = response.status_code == 200 and data and data.get('success')
        print(f"  Status: {response.status_code} {'✅' if results['health_check'] else '❌'}")
        if data:
            print(f"  Response: {data.get('message', 'N/A')}")
    except Exception as e:
        results['health_check'] = False
        print(f"  ❌ Error: {e}")
    
    # Test 3: Create Video Function
    print("\n[TEST 3] Create Video Function")
    try:
        video_data = {
            "title": "Test Video - URL Function Test",
            "description": "Testing the create video function",
            "theme": "nature"
        }
        response = requests.post(
            f"{BASE_URL}/api/generator/create",
            json=video_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        data = response.json() if response.status_code in [200, 201, 202] else None
        results['create_video'] = response.status_code in [200, 201, 202] and data and data.get('success')
        print(f"  Status: {response.status_code} {'✅' if results['create_video'] else '❌'}")
        if data:
            doc_id = data.get('documentary_id')
            print(f"  Documentary ID: {doc_id if doc_id else 'N/A'}")
            print(f"  Message: {data.get('message', 'N/A')}")
    except Exception as e:
        results['create_video'] = False
        print(f"  ❌ Error: {e}")
    
    # Test 4: Debug Routes
    print("\n[TEST 4] Debug Routes Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/api/generator/debug-routes", timeout=10)
        data = response.json() if response.status_code == 200 else None
        results['debug_routes'] = response.status_code == 200 and data and data.get('success')
        print(f"  Status: {response.status_code} {'✅' if results['debug_routes'] else '❌'}")
        if data and 'routes' in data:
            generator_routes = [r for r in data['routes'] if 'generator' in r.get('rule', '').lower()]
            print(f"  Generator Routes Found: {len(generator_routes)}")
    except Exception as e:
        results['debug_routes'] = False
        print(f"  ❌ Error: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")
    
    return passed == total

if __name__ == '__main__':
    success = test_generator_urls()
    sys.exit(0 if success else 1)


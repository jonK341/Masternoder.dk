#!/usr/bin/env python3
"""
Test script for Generator API endpoints
Tests both AI clips and video generation endpoints
"""
import sys
import requests
import json
import time

# Fix UnicodeEncodeError on Windows
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'https://masternoder.dk/vidgenerator'

def test_api_endpoint(method, endpoint, data=None, description=""):
    """Test an API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*80}")
    print(f"Testing: {description}")
    print(f"{'='*80}")
    print(f"Method: {method}")
    print(f"URL: {url}")
    if data:
        print(f"Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    try:
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"Response: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        except:
            print(f"Response (text): {response.text[:500]}")
        
        if response.status_code in [200, 201, 202]:
            print(f"✅ SUCCESS")
            return True
        else:
            print(f"❌ FAILED - Status: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: {e}")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False

def main():
    print("="*80)
    print("GENERATOR API TEST SUITE")
    print("="*80)
    
    results = []
    
    # Test 1: Test route
    results.append((
        "Test Route",
        test_api_endpoint('GET', '/api/generator/test', description="Test Route Health Check")
    ))
    
    # Test 2: Create AI Clip
    clip_data = {
        "prompt": "A beautiful sunset over mountains with dramatic clouds",
        "meta": {
            "duration": 10,
            "style": "cinematic",
            "quality": "high"
        }
    }
    results.append((
        "Create AI Clip",
        test_api_endpoint('POST', '/api/generator/ai-clips', data=clip_data, description="Create AI Clip Generation Job")
    ))
    
    # Test 3: Create Video
    video_data = {
        "title": "Test Video Generation",
        "description": "A test video about nature and wildlife",
        "theme": "nature"
    }
    results.append((
        "Create Video",
        test_api_endpoint('POST', '/api/generator/create', data=video_data, description="Create Video Generation Job")
    ))
    
    # Test 4: Check AI Clip Status (if we got a job_id from test 2)
    # This would require storing the job_id from the previous test
    # For now, we'll use a placeholder
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())


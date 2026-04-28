#!/usr/bin/env python3
"""
Comprehensive Generator Test - Tests all endpoints and identifies reusable components
"""
import sys
import requests
import json
import time

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'https://masternoder.dk/vidgenerator'

def test_endpoint(name, method, url, data=None, expected_status=200, description=""):
    """Test an endpoint and return results"""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    if description:
        print(f"Description: {description}")
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
            return False, None
        
        print(f"\nStatus Code: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        except:
            print(f"Response (text): {response.text[:500]}")
            response_data = None
        
        success = response.status_code == expected_status
        if success:
            print(f"✅ SUCCESS")
        else:
            print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
        
        return success, response_data
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: {e}")
        return False, None
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False, None

def main():
    print("="*80)
    print("COMPREHENSIVE GENERATOR TEST SUITE")
    print("="*80)
    
    results = {}
    
    # Test 1: Health Check
    success, data = test_endpoint(
        "Health Check",
        'GET',
        f"{BASE_URL}/api/generator/test",
        expected_status=200,
        description="Basic health check endpoint"
    )
    results['health_check'] = success
    
    # Test 2: Debug Routes
    success, data = test_endpoint(
        "Debug Routes",
        'GET',
        f"{BASE_URL}/api/generator/debug-routes",
        expected_status=200,
        description="List all registered routes"
    )
    results['debug_routes'] = success
    
    # Test 3: Create AI Clip
    clip_data = {
        "prompt": "A beautiful sunset over mountains with dramatic clouds",
        "meta": {
            "duration": 10,
            "style": "cinematic",
            "quality": "high"
        }
    }
    success, data = test_endpoint(
        "Create AI Clip",
        'POST',
        f"{BASE_URL}/api/generator/ai-clips",
        data=clip_data,
        expected_status=202,
        description="Create an AI clip generation job"
    )
    results['create_ai_clip'] = success
    job_id = data.get('job_id') if data else None
    
    # Test 4: Check AI Clip Status
    if job_id:
        time.sleep(2)  # Wait for job to process
        success, data = test_endpoint(
            "AI Clip Status",
            'GET',
            f"{BASE_URL}/api/generator/ai-clips/{job_id}",
            expected_status=200,
            description="Check status of AI clip generation job"
        )
        results['ai_clip_status'] = success
    
    # Test 5: Create Video
    video_data = {
        "title": "Test Video - Comprehensive Test",
        "description": "A comprehensive test video to verify all generator functionality",
        "theme": "nature",
        "quality": "medium"
    }
    success, data = test_endpoint(
        "Create Video",
        'POST',
        f"{BASE_URL}/api/generator/create",
        data=video_data,
        expected_status=202,
        description="Create a full video generation job"
    )
    results['create_video'] = success
    doc_id = data.get('documentary_id') if data else None
    
    # Test 6: Check Video Progress
    if doc_id:
        print(f"\n{'='*80}")
        print("Polling Video Progress")
        print(f"{'='*80}")
        max_polls = 5
        for i in range(max_polls):
            time.sleep(2)
            success, progress_data = test_endpoint(
                f"Video Progress (Poll {i+1}/{max_polls})",
                'GET',
                f"{BASE_URL}/api/documentary/progress/{doc_id}",
                expected_status=200,
                description="Check video generation progress"
            )
            if progress_data:
                status = progress_data.get('status')
                progress = progress_data.get('progress', 0)
                print(f"  Status: {status}, Progress: {progress}%")
                if status == 'completed':
                    results['video_progress'] = True
                    break
                elif status == 'failed':
                    results['video_progress'] = False
                    break
        else:
            results['video_progress'] = False
    
    # Test 7: Generator Page
    success, data = test_endpoint(
        "Generator Page",
        'GET',
        f"{BASE_URL}/generator",
        expected_status=200,
        description="Load the generator HTML page"
    )
    results['generator_page'] = success
    
    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    
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
    success = main()
    sys.exit(0 if success else 1)


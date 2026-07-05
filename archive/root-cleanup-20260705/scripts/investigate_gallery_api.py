"""Investigate Gallery API 500 error"""
import requests
import json
import sys

BASE_URL = 'https://masternoder.dk'

def test_gallery_api():
    """Test Gallery API and capture detailed error information"""
    print("=" * 70)
    print("Investigating Gallery API Error")
    print("=" * 70)
    print()
    
    # Test the endpoint
    url = f"{BASE_URL}/vidgenerator/api/gallery/list"
    print(f"Testing: {url}")
    print()
    
    try:
        response = requests.get(url, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print()
        
        # Try to get response text
        try:
            response_text = response.text
            print(f"Response Length: {len(response_text)} characters")
            print(f"Response Preview (first 500 chars):")
            print(response_text[:500])
            print()
            
            # Try to parse as JSON
            try:
                response_json = response.json()
                print("Response JSON:")
                print(json.dumps(response_json, indent=2))
            except:
                print("Response is not valid JSON")
        except Exception as e:
            print(f"Error reading response: {e}")
        
        print()
        print("=" * 70)
        
        # Check if it's actually returning 200 but test script thinks it's 500
        if response.status_code == 200:
            print("[OK] API is actually returning 200!")
            return True
        elif response.status_code == 500:
            print("[FAIL] API is returning 500")
            return False
        else:
            print(f"[WARN] Unexpected status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request failed: {e}")
        return False

def test_with_different_params():
    """Test with different query parameters"""
    print()
    print("=" * 70)
    print("Testing with Different Parameters")
    print("=" * 70)
    print()
    
    test_cases = [
        {'params': {}, 'name': 'No parameters'},
        {'params': {'status': 'all'}, 'name': 'Status: all'},
        {'params': {'status': 'completed'}, 'name': 'Status: completed'},
        {'params': {'search': 'test'}, 'name': 'With search'},
        {'params': {'sort': 'newest'}, 'name': 'Sort: newest'},
    ]
    
    for test_case in test_cases:
        print(f"Test: {test_case['name']}")
        url = f"{BASE_URL}/vidgenerator/api/gallery/list"
        
        try:
            response = requests.get(url, params=test_case['params'], timeout=10)
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  Videos: {data.get('count', 0)}")
                except:
                    pass
        except Exception as e:
            print(f"  Error: {e}")
        print()

if __name__ == '__main__':
    success = test_gallery_api()
    test_with_different_params()
    
    if success:
        print("\n[OK] Gallery API is working!")
        sys.exit(0)
    else:
        print("\n[FAIL] Gallery API needs investigation")
        sys.exit(1)

#!/usr/bin/env python3
"""
Complete test of API Debugger page with URL display
"""

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://masternoder.dk/vidgenerator"

def test_complete():
    """Complete test"""
    print("=" * 70)
    print("Complete API Debugger Test")
    print("=" * 70)
    print()
    
    # Test main page (try both URLs)
    urls_to_test = [
        BASE_URL + "/api/debugger",
        BASE_URL + "/vidgenerator/api/debugger",
    ]
    
    for url in urls_to_test:
        print(f"Testing: {url}")
        try:
            response = requests.get(url, timeout=10, verify=False)
            if response.status_code == 200:
                print(f"✅ Page loaded: {response.status_code}")
                
                # Check for key elements
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Check for URL display
                url_element = soup.find(id='currentUrl')
                if url_element:
                    print(f"✅ URL display found: {url_element.text[:80]}...")
                else:
                    print("⚠️  URL display NOT found (may be old template)")
                
                # Check for rettigheder section
                rettigheder_section = soup.find('h2', string=lambda x: x and 'Rettigheder' in x)
                if rettigheder_section:
                    print("✅ Rettigheder section found")
                else:
                    print("⚠️  Rettigheder section NOT found (may be old template)")
                
                # Check for checkboxes
                checkboxes = soup.find_all('input', type='checkbox')
                if checkboxes:
                    print(f"✅ Found {len(checkboxes)} rettigheder checkboxes")
                else:
                    print("⚠️  No checkboxes found")
                
                # Check for Slå button
                slaa_btn = soup.find('button', id='slaaBtn')
                if slaa_btn:
                    print(f"✅ Slå button found: {slaa_btn.text}")
                else:
                    print("⚠️  Slå button NOT found")
                
                # Check for API testing section
                api_section = soup.find('h2', string=lambda x: x and 'API Testing' in x)
                if api_section:
                    print("✅ API Testing section found")
                else:
                    print("⚠️  API Testing section NOT found")
                
                print()
                break  # Found working URL, stop testing
                    
            else:
                print(f"❌ Page failed: {response.status_code}")
                print()
        except Exception as e:
            print(f"❌ Error: {e}")
            print()
    
    print()
    
    # Test rettigheder API
    print("Testing Rettigheder API:")
    print("-" * 70)
    
    api_endpoints = [
        ("/api/rettigheder/list", "GET"),
        ("/api/rettigheder/status", "GET"),
    ]
    
    for endpoint, method in api_endpoints:
        full_url = BASE_URL + endpoint
        try:
            if method == "GET":
                response = requests.get(full_url, timeout=5, verify=False)
            else:
                response = requests.post(full_url, json={}, timeout=5, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {method} {endpoint}: {response.status_code}")
                if 'rettigheder' in data:
                    print(f"   → Found {len(data.get('rettigheder', []))} rettigheder")
                elif 'status' in data:
                    print(f"   → Status data received")
            else:
                print(f"❌ {method} {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {method} {endpoint}: Error - {e}")
    
    print()
    print("=" * 70)
    print("Test Complete")
    print("=" * 70)
    print()
    print(f"🌐 Visit the page: {BASE_URL}/api/debugger")

if __name__ == '__main__':
    test_complete()


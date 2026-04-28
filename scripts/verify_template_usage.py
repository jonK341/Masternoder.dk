#!/usr/bin/env python3
"""
Verify which template is being used
"""

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://masternoder.dk/vidgenerator"

def verify():
    """Verify template"""
    print("=" * 70)
    print("Verifying Template Usage")
    print("=" * 70)
    print()
    
    url = BASE_URL + "/api/debugger"
    response = requests.get(url, timeout=10, verify=False)
    
    if response.status_code == 200:
        html = response.text
        
        # Check for new template markers
        has_rettigheder = "Rettigheder" in html and "rettigheder-grid" in html
        has_url_display = "currentUrl" in html
        has_slaa_btn = "slaaBtn" in html
        has_gradient = "linear-gradient(135deg" in html
        
        # Check for old template markers
        has_old_style = "font-family: monospace" in html and "background: #0a0a0a" in html
        
        print("Template Analysis:")
        print("-" * 70)
        print(f"Has new template (Rettigheder grid): {has_rettigheder}")
        print(f"Has URL display: {has_url_display}")
        print(f"Has Slå button: {has_slaa_btn}")
        print(f"Has gradient background: {has_gradient}")
        print(f"Has old template (monospace): {has_old_style}")
        print()
        
        if has_rettigheder and has_url_display:
            print("✅ NEW TEMPLATE IS BEING USED!")
        elif has_old_style:
            print("❌ OLD FALLBACK TEMPLATE IS BEING USED")
            print("   This means template file is not found or there's an exception")
        else:
            print("⚠️  UNKNOWN TEMPLATE VERSION")
        
        # Show first 500 chars
        print()
        print("First 500 characters of response:")
        print("-" * 70)
        print(html[:500])
        
    else:
        print(f"❌ Page failed: {response.status_code}")

if __name__ == '__main__':
    verify()


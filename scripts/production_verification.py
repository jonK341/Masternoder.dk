#!/usr/bin/env python3
"""
Production Verification - Complete system test
"""

import requests
import urllib3
from bs4 import BeautifulSoup
import json
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://masternoder.dk/vidgenerator"

def verify_production():
    """Complete production verification"""
    print("=" * 70)
    print("PRODUCTION VERIFICATION")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    results = {
        'pages': [],
        'apis': [],
        'features': []
    }
    
    # Test Main Pages
    print("📄 Testing Main Pages:")
    print("-" * 70)
    
    pages = [
        ("/", "Home"),
        ("/generator", "Generator"),
        ("/gallery", "Gallery"),
        ("/game", "Game"),
        ("/api/debugger", "API Debugger"),
    ]
    
    for path, name in pages:
        url = BASE_URL + path
        try:
            response = requests.get(url, timeout=10, verify=False)
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {name}: {response.status_code}")
            results['pages'].append({
                'name': name,
                'status': response.status_code,
                'success': response.status_code == 200
            })
        except Exception as e:
            print(f"❌ {name}: Error - {str(e)[:50]}")
            results['pages'].append({
                'name': name,
                'status': 'error',
                'success': False
            })
    
    print()
    
    # Test API Endpoints
    print("🔌 Testing API Endpoints:")
    print("-" * 70)
    
    api_endpoints = [
        ("/api/gallery/list", "GET", None, "Gallery List"),
        ("/api/rettigheder/list", "GET", None, "Rettigheder List"),
        ("/api/rettigheder/status", "GET", None, "Rettigheder Status"),
        ("/api/debug/errors/scan", "GET", None, "Debug Scan"),
    ]
    
    for path, method, data, name in api_endpoints:
        url = BASE_URL + path
        try:
            if method == "GET":
                response = requests.get(url, timeout=10, verify=False)
            else:
                response = requests.post(url, json=data, timeout=10, verify=False)
            
            is_ok = response.status_code in [200, 201, 405]
            status = "✅" if is_ok else "❌"
            print(f"{status} {name}: {response.status_code}")
            results['apis'].append({
                'name': name,
                'status': response.status_code,
                'success': is_ok
            })
        except Exception as e:
            print(f"❌ {name}: Error - {str(e)[:50]}")
            results['apis'].append({
                'name': name,
                'status': 'error',
                'success': False
            })
    
    print()
    
    # Test API Debugger Features
    print("🎨 Testing API Debugger Features:")
    print("-" * 70)
    
    debugger_url = BASE_URL + "/api/debugger"
    try:
        response = requests.get(debugger_url, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            features = [
                ("URL Display", soup.find(id='currentUrl')),
                ("Rettigheder Section", soup.find('h2', string=lambda x: x and 'Rettigheder' in x)),
                ("Rettigheder Grid", soup.find(id='rettighederGrid')),
                ("Slå Button", soup.find(id='slaaBtn')),
                ("API Testing Section", soup.find('h2', string=lambda x: x and 'API Testing' in x)),
            ]
            
            for name, element in features:
                status = "✅" if element else "❌"
                print(f"{status} {name}")
                results['features'].append({
                    'name': name,
                    'success': element is not None
                })
        else:
            print(f"❌ API Debugger page failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing features: {str(e)[:50]}")
    
    print()
    
    # Test Slå Functionality
    print("⚡ Testing Slå Functionality:")
    print("-" * 70)
    
    slaa_url = BASE_URL + "/api/rettigheder/slaa"
    try:
        response = requests.post(
            slaa_url,
            json={"rettigheder": ["Musik", "TV"]},
            headers={"Content-Type": "application/json"},
            timeout=10,
            verify=False
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Slå Function: Working")
                print(f"   Message: {data.get('message', 'N/A')}")
                results['features'].append({
                    'name': 'Slå Function',
                    'success': True
                })
            else:
                print(f"⚠️  Slå Function: Returned success=False")
                results['features'].append({
                    'name': 'Slå Function',
                    'success': False
                })
        else:
            print(f"❌ Slå Function: Status {response.status_code}")
            results['features'].append({
                'name': 'Slå Function',
                'success': False
            })
    except Exception as e:
        print(f"❌ Slå Function: Error - {str(e)[:50]}")
        results['features'].append({
            'name': 'Slå Function',
            'success': False
        })
    
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    pages_ok = sum(1 for p in results['pages'] if p['success'])
    apis_ok = sum(1 for a in results['apis'] if a['success'])
    features_ok = sum(1 for f in results['features'] if f['success'])
    
    print(f"Pages: {pages_ok}/{len(results['pages'])} ✅")
    print(f"APIs: {apis_ok}/{len(results['apis'])} ✅")
    print(f"Features: {features_ok}/{len(results['features'])} ✅")
    print()
    
    total_tests = len(results['pages']) + len(results['apis']) + len(results['features'])
    total_ok = pages_ok + apis_ok + features_ok
    success_rate = (total_ok / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Overall Success Rate: {success_rate:.1f}% ({total_ok}/{total_tests})")
    print()
    
    if success_rate >= 95:
        print("🎉 PRODUCTION STATUS: ✅ EXCELLENT")
    elif success_rate >= 80:
        print("✅ PRODUCTION STATUS: ✅ GOOD")
    else:
        print("⚠️  PRODUCTION STATUS: ⚠️  NEEDS ATTENTION")
    
    print()
    print("=" * 70)
    print("🌐 Live URL: https://masternoder.dk/vidgenerator/api/debugger")
    print("=" * 70)

if __name__ == '__main__':
    verify_production()


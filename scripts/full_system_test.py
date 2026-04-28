#!/usr/bin/env python3
"""
Full System Test
Test everything: database, APIs, frontend connections
"""
import os
import sys
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "https://masternoder.dk"
TEST_USER = "default_user"

def test_database():
    """Test database"""
    print("Testing database...")
    try:
        from src.app import create_app
        from src.db.models import db
        from sqlalchemy import text
        
        app = create_app()
        with app.app_context():
            tables = ['user_profiles', 'onboarding_progress', 'player_levels', 
                     'xp_history', 'daily_activities', 'user_agent_skills', 'rewards']
            
            results = {}
            for table in tables:
                try:
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    results[table] = count
                    print(f"  ✓ {table}: {count} records")
                except Exception as e:
                    results[table] = -1
                    print(f"  ✗ {table}: {e}")
            
            return all(v >= 0 for v in results.values())
    except Exception as e:
        print(f"  ✗ Database test failed: {e}")
        return False

def test_apis():
    """Test APIs"""
    print("\nTesting APIs...")
    endpoints = [
        f"{BASE_URL}/vidgenerator/api/user/profile/{TEST_USER}/display",
        f"{BASE_URL}/vidgenerator/api/user/onboarding/status/{TEST_USER}",
        f"{BASE_URL}/vidgenerator/api/user/agent-skills/{TEST_USER}",
        f"{BASE_URL}/vidgenerator/api/agents/controller/status",
        f"{BASE_URL}/vidgenerator/api/shop/currency?user_id={TEST_USER}",
    ]
    
    passed = 0
    for url in endpoints:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                print(f"  ✓ {url.split('/')[-1]}: {r.status_code}")
                passed += 1
            else:
                print(f"  ✗ {url.split('/')[-1]}: {r.status_code}")
        except Exception as e:
            print(f"  ✗ {url.split('/')[-1]}: {e}")
    
    return passed == len(endpoints)

def test_pages():
    """Test pages"""
    print("\nTesting pages...")
    pages = [
        f"{BASE_URL}/vidgenerator/profile",
        f"{BASE_URL}/vidgenerator/stats",
        f"{BASE_URL}/vidgenerator/social",
        f"{BASE_URL}/vidgenerator/dashboard",
    ]
    
    passed = 0
    for url in pages:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                print(f"  ✓ {url.split('/')[-1]}: {r.status_code}")
                passed += 1
            else:
                print(f"  ✗ {url.split('/')[-1]}: {r.status_code}")
        except Exception as e:
            print(f"  ✗ {url.split('/')[-1]}: {e}")
    
    return passed == len(pages)

def main():
    """Run all tests"""
    print("=" * 70)
    print("FULL SYSTEM TEST")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    db_ok = test_database()
    api_ok = test_apis()
    page_ok = test_pages()
    
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Database: {'✓ PASS' if db_ok else '✗ FAIL'}")
    print(f"APIs: {'✓ PASS' if api_ok else '✗ FAIL'}")
    print(f"Pages: {'✓ PASS' if page_ok else '✗ FAIL'}")
    print()
    
    all_ok = db_ok and api_ok and page_ok
    print(f"Overall: {'✓ ALL SYSTEMS OPERATIONAL' if all_ok else '✗ SOME ISSUES DETECTED'}")
    
    return all_ok

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

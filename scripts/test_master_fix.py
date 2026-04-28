"""
Test Master Fix Script
Tests all components of the master fix system
"""
import os
import sys
import json
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def test_imports():
    """Test that all required modules can be imported"""
    print("=" * 80)
    print("TEST 1: Testing Imports")
    print("=" * 80)
    
    tests = []
    
    # Test API Scanner
    try:
        from backend.services.api_scanner import APIScanner, api_scanner
        tests.append(("API Scanner", True, None))
        print("✅ API Scanner imported successfully")
    except Exception as e:
        tests.append(("API Scanner", False, str(e)))
        print(f"❌ API Scanner import failed: {e}")
    
    # Test API Scanner Routes
    try:
        from backend.routes.api_scanner_routes import api_scanner_bp
        tests.append(("API Scanner Routes", True, None))
        print("✅ API Scanner Routes imported successfully")
    except Exception as e:
        tests.append(("API Scanner Routes", False, str(e)))
        print(f"❌ API Scanner Routes import failed: {e}")
    
    # Test Blueprint Registration
    try:
        from backend.register_blueprints import register_all_blueprints
        tests.append(("Blueprint Registration", True, None))
        print("✅ Blueprint Registration imported successfully")
    except Exception as e:
        tests.append(("Blueprint Registration", False, str(e)))
        print(f"❌ Blueprint Registration import failed: {e}")
    
    # Test Hunters Game Routes
    try:
        from backend.routes.hunters_game import hunters_game_bp
        tests.append(("Hunters Game Routes", True, None))
        print("✅ Hunters Game Routes imported successfully")
    except Exception as e:
        tests.append(("Hunters Game Routes", False, str(e)))
        print(f"❌ Hunters Game Routes import failed: {e}")
    
    return tests

def test_api_scanner():
    """Test API Scanner functionality"""
    print()
    print("=" * 80)
    print("TEST 2: Testing API Scanner")
    print("=" * 80)
    
    try:
        from backend.services.api_scanner import APIScanner
        
        scanner = APIScanner(BASE_DIR)
        
        # Test scanning
        print("Testing blueprint scanning...")
        blueprints = scanner.scan_blueprints()
        print(f"✅ Found {len(blueprints)} blueprints")
        
        print("Testing route scanning...")
        routes = scanner.scan_routes()
        print(f"✅ Found {len(routes)} routes")
        
        print("Testing service scanning...")
        services = scanner.scan_services()
        print(f"✅ Found {len(services)} services")
        
        print("Testing missing method detection...")
        missing = scanner.find_missing_methods()
        print(f"✅ Found {len(missing)} missing methods")
        
        print("Testing report generation...")
        report = scanner.get_report()
        print(f"✅ Report generated: {report['summary']}")
        
        return True
    except Exception as e:
        print(f"❌ API Scanner test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_blueprint_registration():
    """Test blueprint registration"""
    print()
    print("=" * 80)
    print("TEST 3: Testing Blueprint Registration")
    print("=" * 80)
    
    try:
        from flask import Flask
        from backend.register_blueprints import register_all_blueprints
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        print("Registering blueprints...")
        count = register_all_blueprints(app)
        print(f"✅ Registered {count} blueprints")
        
        # Check for API scanner blueprint
        registered_names = [bp.name for bp in app.blueprints.values()]
        if 'api_scanner' in registered_names:
            print("✅ API Scanner blueprint registered")
        else:
            print("⚠️ API Scanner blueprint not found in registered blueprints")
            print(f"Registered: {registered_names}")
        
        # Check for hunters_game blueprint
        if 'hunters_game' in registered_names:
            print("✅ Hunters Game blueprint registered")
        else:
            print("⚠️ Hunters Game blueprint not found")
        
        return True
    except Exception as e:
        print(f"❌ Blueprint registration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_endpoints():
    """Test that endpoints are accessible"""
    print()
    print("=" * 80)
    print("TEST 4: Testing Endpoints")
    print("=" * 80)
    
    try:
        from flask import Flask
        from backend.register_blueprints import register_all_blueprints
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        register_all_blueprints(app)
        
        # Get all registered routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'rule': rule.rule,
                'methods': list(rule.methods),
                'endpoint': rule.endpoint
            })
        
        print(f"✅ Found {len(routes)} total routes")
        
        # Check for scanner endpoints
        scanner_routes = [r for r in routes if 'scanner' in r['rule']]
        print(f"✅ Found {len(scanner_routes)} scanner routes")
        
        # Check for hunters_game endpoints
        hunters_routes = [r for r in routes if 'hunters' in r['rule']]
        print(f"✅ Found {len(hunters_routes)} hunters_game routes")
        
        # List some key routes
        key_routes = [
            '/api/debugger/scanner/scan',
            '/api/debugger/scanner/blueprints',
            '/api/game/hunters/level',
            '/api/game/hunters/rewards'
        ]
        
        found_key = []
        for key_route in key_routes:
            for route in routes:
                if key_route in route['rule']:
                    found_key.append(key_route)
                    break
        
        print(f"✅ Found {len(found_key)}/{len(key_routes)} key routes")
        for route in found_key:
            print(f"   - {route}")
        
        return True
    except Exception as e:
        print(f"❌ Endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_files_exist():
    """Test that all required files exist"""
    print()
    print("=" * 80)
    print("TEST 5: Testing File Existence")
    print("=" * 80)
    
    required_files = [
        'backend/services/api_scanner.py',
        'backend/routes/api_scanner_routes.py',
        'backend/register_blueprints.py',
        'backend/routes/hunters_game.py',
        'vidgenerator/debugger/index.html',
        'scripts/fix_all_loose_ends_master.py'
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = os.path.join(BASE_DIR, file_path)
        exists = os.path.exists(full_path)
        if exists:
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - NOT FOUND")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests"""
    print("=" * 80)
    print("MASTER FIX TEST SUITE")
    print("=" * 80)
    print()
    
    results = {
        'imports': test_imports(),
        'api_scanner': test_api_scanner(),
        'blueprint_registration': test_blueprint_registration(),
        'endpoints': test_endpoints(),
        'files': test_files_exist()
    }
    
    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("⚠️ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())

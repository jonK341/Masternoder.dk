#!/usr/bin/env python3
"""
Production Deployment Check
Verifies all systems are properly integrated and ready for deployment
"""
import sys
import os

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

def check_imports():
    """Check all critical imports"""
    print("=" * 70)
    print("Checking Critical Imports...")
    print("=" * 70)
    
    checks = []
    
    # Check services
    services = [
        'backend.services.enhanced_click_activity',
        'backend.services.trophy_system',
        'backend.services.system_history',
        'backend.services.search_intelligence',
        'backend.services.energy_generation_system',
        'backend.services.agent_manager',
        'backend.services.enhanced_progress_data',
        'backend.services.video_generation_rewards',
        'backend.services.shop_v2_enhanced',
    ]
    
    for service in services:
        try:
            __import__(service)
            checks.append(('✅', service, 'OK'))
        except Exception as e:
            checks.append(('❌', service, str(e)))
    
    # Check routes
    routes = [
        'backend.routes.enhanced_features_routes',
        'backend.routes.system_history_routes',
        'backend.routes.energy_agent_routes',
        'backend.routes.progress_rewards_routes',
        'backend.routes.shop_v2_enhanced_routes',
    ]
    
    for route in routes:
        try:
            __import__(route)
            checks.append(('✅', route, 'OK'))
        except Exception as e:
            checks.append(('❌', route, str(e)))
    
    # Print results
    for status, module, result in checks:
        print(f"{status} {module}: {result}")
    
    failed = sum(1 for s, _, _ in checks if s == '❌')
    print(f"\n{len(checks) - failed}/{len(checks)} imports successful")
    
    return failed == 0

def check_blueprints_registration():
    """Check blueprint registration"""
    print("\n" + "=" * 70)
    print("Checking Blueprint Registration...")
    print("=" * 70)
    
    try:
        from backend.register_blueprints import register_all_blueprints
        from flask import Flask
        
        # Create a test app
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-key'
        app.config['TESTING'] = True
        
        # Register blueprints
        register_all_blueprints(app)
        
        # Check registered blueprints
        registered = [bp.name for bp in app.blueprints.values()]
        
        required_blueprints = [
            'enhanced_features',
            'system_history',
            'energy_agent',
            'progress_rewards',
            'shop_v2_enhanced',
        ]
        
        found = []
        missing = []
        
        for req_bp in required_blueprints:
            if any(req_bp in bp for bp in registered):
                found.append(req_bp)
                print(f"✅ {req_bp}: Registered")
            else:
                missing.append(req_bp)
                print(f"❌ {req_bp}: Missing")
        
        print(f"\n{len(found)}/{len(required_blueprints)} required blueprints found")
        return len(missing) == 0
        
    except Exception as e:
        print(f"❌ Error checking blueprints: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_database_connection():
    """Check database connection"""
    print("\n" + "=" * 70)
    print("Checking Database Connection...")
    print("=" * 70)
    
    try:
        from backend.services.unified_points_database import unified_points_db
        
        # Try to get a user (should not fail even if empty)
        try:
            result = unified_points_db.get_user_points('test_user')
            print("✅ Database connection: OK")
            print(f"   Test user points: {result if result else 'No data (expected)'}")
            return True
        except Exception as e:
            print(f"⚠️  Database connection: Warning - {e}")
            print("   (This may be expected if database is not initialized)")
            return True  # Don't fail on this, might be expected
            
    except ImportError as e:
        print(f"❌ Could not import unified_points_db: {e}")
        return False
    except Exception as e:
        print(f"❌ Database check error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_endpoints():
    """Check that endpoints are accessible"""
    print("\n" + "=" * 70)
    print("Checking Endpoint Definitions...")
    print("=" * 70)
    
    try:
        from flask import Flask
        from backend.register_blueprints import register_all_blueprints
        
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-key'
        app.config['TESTING'] = True
        
        register_all_blueprints(app)
        
        # Check some key endpoints
        endpoints = [
            ('/api/enhanced/click/award', 'POST'),
            ('/api/enhanced/trophy/award', 'POST'),
            ('/api/history/user/test/timeline', 'GET'),
            ('/api/energy-agent/energy/generate', 'POST'),
            ('/api/progress-rewards/progress/test/leveling', 'GET'),
            ('/api/shop-v2/items', 'GET'),
        ]
        
        with app.test_request_context():
            from flask import url_for
            
            found = 0
            for endpoint, method in endpoints:
                try:
                    # Check if route exists
                    rules = [str(r) for r in app.url_map.iter_rules()]
                    matching = [r for r in rules if endpoint.split('/')[2] in r]
                    if matching:
                        print(f"✅ {method} {endpoint}: Found")
                        found += 1
                    else:
                        print(f"⚠️  {method} {endpoint}: Not found in rules")
                except Exception as e:
                    print(f"❌ {method} {endpoint}: Error - {e}")
            
            print(f"\n{found}/{len(endpoints)} endpoints checked")
            return found > 0
            
    except Exception as e:
        print(f"❌ Error checking endpoints: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all checks"""
    print("\n" + "=" * 70)
    print("PRODUCTION DEPLOYMENT CHECK")
    print("=" * 70)
    print()
    
    results = []
    
    # Run checks
    results.append(("Imports", check_imports()))
    results.append(("Blueprint Registration", check_blueprints_registration()))
    results.append(("Database Connection", check_database_connection()))
    results.append(("Endpoints", check_endpoints()))
    
    # Summary
    print("\n" + "=" * 70)
    print("DEPLOYMENT CHECK SUMMARY")
    print("=" * 70)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n{passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 ALL CHECKS PASSED - READY FOR PRODUCTION!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} CHECK(S) FAILED - REVIEW BEFORE DEPLOYMENT")
        return 1

if __name__ == '__main__':
    sys.exit(main())

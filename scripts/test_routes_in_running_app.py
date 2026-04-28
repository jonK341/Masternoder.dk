#!/usr/bin/env python3
"""
Test Routes in Running App
Tests if routes are registered in the running app instance
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def test_routes():
    """Test routes"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Test route directly via uWSGI
        print("[1/2] Testing route directly via uWSGI...")
        stdin, stdout, stderr = ssh.exec_command(
            "curl -s http://127.0.0.1:5000/api/monetization/top50?limit=6 2>&1 | head -10",
            timeout=10
        )
        response = stdout.read().decode().strip()
        if 'success' in response.lower() or 'top50' in response.lower():
            print("  ✅ Route works via uWSGI")
            print(f"  Response: {response[:200]}")
        elif '404' in response or 'Not Found' in response:
            print("  ❌ Route returns 404 via uWSGI")
        else:
            print(f"  ⚠️  Unexpected response: {response[:200]}")
        
        # Check what routes are actually registered
        print()
        print("[2/2] Checking registered routes...")
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html/vidgenerator")

try:
    from src.app import create_app
    app = create_app()
    
    # Check for specific routes
    routes_to_find = [
        '/api/monetization/top50',
        '/api/monetization/cash',
        '/api/tech-tree/knowledge',
        '/api/agent/get-all',
        '/api/points/statistics',
        '/api/points/calculator/predict',
    ]
    
    print("Checking routes in app...")
    found_routes = []
    for target_route in routes_to_find:
        found = False
        for rule in app.url_map.iter_rules():
            rule_str = str(rule)
            if target_route in rule_str:
                found = True
                found_routes.append((target_route, rule_str))
                break
        if not found:
            print(f"  ❌ {target_route} NOT FOUND")
    
    if found_routes:
        print(f"\\n✅ Found {len(found_routes)} routes:")
        for target, rule in found_routes:
            print(f"  {target} -> {rule[:60]}")
    
    # Also check blueprint registration
    print("\\nChecking blueprints...")
    blueprint_names = [bp.name for bp in app.blueprints.values()]
    required_blueprints = ['monetization_top50', 'agent', 'tech_tree', 'point_calculator', 'unified_points']
    for bp_name in required_blueprints:
        if bp_name in blueprint_names:
            print(f"  ✅ {bp_name} blueprint registered")
        else:
            print(f"  ❌ {bp_name} blueprint NOT registered")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
'''
        
        stdin2, stdout2, stderr2 = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=60
        )
        output = stdout2.read().decode().strip()
        error = stderr2.read().decode().strip()
        if output:
            print(output)
        if error and "Traceback" in error:
            print(f"\n[ERROR OUTPUT]\n{error[:500]}")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_routes()

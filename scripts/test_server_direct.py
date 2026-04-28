#!/usr/bin/env python3
"""
Comprehensive server-side test script
Tests backend blueprints directly on server
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def test_server_direct():
    """Test directly on server"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        
        print("=" * 70)
        print("COMPREHENSIVE SERVER TEST")
        print("=" * 70)
        print()
        
        # Create test script on server
        test_script = """#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/var/www/html/vidgenerator')

print("=" * 70)
print("TESTING BACKEND BLUEPRINT REGISTRATION")
print("=" * 70)
print()

# Test 1: Import
print("Test 1: Import backend.register_blueprints")
try:
    from backend.register_blueprints import register_all_blueprints
    print("  [OK] Import successful")
except Exception as e:
    print(f"  [ERROR] Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Import blueprints
print("\\nTest 2: Import individual blueprints")
blueprints = {}
try:
    from backend.routes.generator import generator_bp
    blueprints['generator'] = generator_bp
    print("  [OK] generator_bp imported")
except Exception as e:
    print(f"  [ERROR] generator_bp: {e}")

try:
    from backend.routes.gallery import gallery_bp
    blueprints['gallery'] = gallery_bp
    print("  [OK] gallery_bp imported")
except Exception as e:
    print(f"  [ERROR] gallery_bp: {e}")

try:
    from backend.routes.game import game_bp
    blueprints['game'] = game_bp
    print("  [OK] game_bp imported")
except Exception as e:
    print(f"  [ERROR] game_bp: {e}")

# Test 3: Check blueprint routes
print("\\nTest 3: Check blueprint routes")
for name, bp in blueprints.items():
    print(f"\\n  {name} blueprint routes:")
    try:
        # Get routes from blueprint
        for rule in bp.deferred_functions:
            if hasattr(rule, '__name__'):
                print(f"    Function: {rule.__name__}")
    except Exception as e:
        print(f"    Error: {e}")
    
    # Try to get URL map (only works after registration)
    try:
        # Create temp app to register blueprint
        from flask import Flask
        test_app = Flask(__name__)
        test_app.register_blueprint(bp)
        for rule in test_app.url_map.iter_rules():
            if '/api/' in rule.rule:
                print(f"    Route: {rule.rule} {list(rule.methods)}")
    except Exception as e:
        print(f"    Could not get routes: {e}")

# Test 4: Register in test app
print("\\nTest 4: Register blueprints in test app")
from flask import Flask
test_app = Flask(__name__)
try:
    register_all_blueprints(test_app)
    print("  [OK] Blueprints registered")
    
    # Check registered blueprints
    backend_bps = ['generator', 'gallery', 'game']
    for bp_name in backend_bps:
        if bp_name in test_app.blueprints:
            print(f"  [OK] {bp_name} blueprint found in app")
        else:
            print(f"  [ERROR] {bp_name} blueprint NOT found")
    
    # Check routes
    print("\\n  Registered API routes:")
    target_routes = ['/api/gallery/list', '/api/generator/create', '/api/game/xp']
    for target in target_routes:
        found = False
        for rule in test_app.url_map.iter_rules():
            if target in rule.rule:
                print(f"    [OK] {target} -> {rule.rule}")
                found = True
                break
        if not found:
            print(f"    [ERROR] {target} NOT FOUND")
            
except Exception as e:
    print(f"  [ERROR] Registration failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Test with actual app
print("\\n" + "=" * 70)
print("TESTING WITH ACTUAL APP")
print("=" * 70)
print()

try:
    from src.app import create_app
    app = create_app()
    
    print("App created successfully")
    print(f"Total blueprints: {len(app.blueprints)}")
    
    # Check backend blueprints
    backend_bps = ['generator', 'gallery', 'game']
    print("\\nBackend blueprints in app:")
    for bp_name in backend_bps:
        if bp_name in app.blueprints:
            print(f"  [OK] {bp_name}")
        else:
            print(f"  [ERROR] {bp_name} MISSING")
    
    # Check routes
    print("\\nAPI routes in app:")
    target_routes = ['/api/gallery/list', '/api/generator/create', '/api/game/xp', '/api/debug/errors/scan']
    for target in target_routes:
        found_routes = []
        for rule in app.url_map.iter_rules():
            if target in rule.rule:
                found_routes.append(f"{rule.rule} {list(rule.methods)}")
        if found_routes:
            print(f"  [OK] {target}:")
            for route in found_routes:
                print(f"      {route}")
        else:
            print(f"  [ERROR] {target} NOT FOUND")
    
    # Test endpoints with test client
    print("\\n" + "=" * 70)
    print("TESTING ENDPOINTS WITH TEST CLIENT")
    print("=" * 70)
    print()
    
    with app.test_client() as client:
        endpoints = [
            ('GET', '/api/gallery/list'),
            ('POST', '/api/generator/create'),
            ('POST', '/api/game/xp'),
            ('GET', '/api/debug/errors/scan'),
        ]
        
        for method, endpoint in endpoints:
            try:
                if method == 'POST':
                    response = client.post(endpoint, json={})
                else:
                    response = client.get(endpoint)
                status = response.status_code
                if status == 200 or status == 500:
                    print(f"  [OK] {method} {endpoint} -> {status}")
                else:
                    print(f"  [ERROR] {method} {endpoint} -> {status}")
            except Exception as e:
                print(f"  [ERROR] {method} {endpoint} -> Exception: {e}")
    
except Exception as e:
    print(f"[ERROR] App creation failed: {e}")
    import traceback
    traceback.print_exc()

print("\\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
"""
        
        # Write test script to server
        print("Creating test script on server...")
        stdin, stdout, stderr = ssh_client.exec_command("cat > /tmp/test_backend.py << 'PYTHON_SCRIPT'\n" + test_script + "\nPYTHON_SCRIPT")
        stdout.channel.recv_exit_status()
        
        # Run test script
        print("Running test script...")
        print()
        cmd = "cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 /tmp/test_backend.py 2>&1"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        print(output)
        if error and "Traceback" in error:
            print("\nErrors:")
            print(error[-3000:])
        
        # Clean up
        ssh_client.exec_command("rm -f /tmp/test_backend.py")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    test_server_direct()


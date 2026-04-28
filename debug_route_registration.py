#!/usr/bin/env python3
"""
Debug route registration and test app directly
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEBUGGING ROUTE REGISTRATION")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

# Test app creation and route listing
print("[1] Testing app creation and listing ALL routes...")
test_code = """
import sys
import os
sys.path.insert(0, '/var/www/html/vidgenerator')
os.chdir('/var/www/html/vidgenerator')

try:
    from src.app import create_app
    app = create_app()
    
    # List all routes
    print("=== ALL REGISTERED ROUTES ===")
    all_routes = list(app.url_map.iter_rules())
    print(f"Total routes: {len(all_routes)}")
    
    # Find parent-controls routes
    parent_routes = [r for r in all_routes if 'parent' in r.rule.lower() or 'parent' in r.endpoint.lower()]
    print(f"\\nParent-related routes: {len(parent_routes)}")
    for route in parent_routes:
        print(f"  {route.rule} [{', '.join(route.methods)}] -> {route.endpoint}")
    
    # Check blueprints
    print(f"\\n=== BLUEPRINTS ===")
    blueprints = list(app.blueprints.keys())
    print(f"Total blueprints: {len(blueprints)}")
    if 'parent_controls' in blueprints:
        print("✓ parent_controls blueprint found")
        bp = app.blueprints['parent_controls']
        print(f"  URL prefix: {bp.url_prefix}")
        print(f"  Name: {bp.name}")
    else:
        print("✗ parent_controls blueprint NOT found")
        print(f"  Available: {[b for b in blueprints if 'parent' in b.lower()]}")
    
    # Test route matching
    print(f"\\n=== TESTING ROUTE MATCHING ===")
    from flask import Flask
    with app.test_request_context('/api/parent-controls/parent-groups'):
        matched = False
        for rule in app.url_map.iter_rules():
            try:
                if rule.match('/api/parent-controls/parent-groups'):
                    print(f"✓ Matched: {rule.rule} -> {rule.endpoint}")
                    matched = True
                    break
            except:
                pass
        if not matched:
            print("✗ No route matched /api/parent-controls/parent-groups")
    
    # Try with vidgenerator prefix
    with app.test_request_context('/vidgenerator/api/parent-controls/parent-groups'):
        matched = False
        for rule in app.url_map.iter_rules():
            try:
                if rule.match('/vidgenerator/api/parent-controls/parent-groups'):
                    print(f"✓ Matched: {rule.rule} -> {rule.endpoint}")
                    matched = True
                    break
            except:
                pass
        if not matched:
            print("✗ No route matched /vidgenerator/api/parent-controls/parent-groups")
            
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
"""
stdin, stdout, stderr = ssh.exec_command(f"cd /var/www/html/vidgenerator && python3 -c {repr(test_code)} 2>&1")
route_debug = stdout.read().decode('utf-8')
print(route_debug)
print()

# Check if APPLICATION_ROOT is affecting routes
print("[2] Checking APPLICATION_ROOT configuration...")
stdin, stdout, stderr = ssh.exec_command("grep -i 'APPLICATION_ROOT\\|application_root' /var/www/html/vidgenerator/src/app.py | head -5")
app_root = stdout.read().decode('utf-8')
print(app_root)
print()

ssh.close()

print("=" * 80)
print("[OK] DEBUG COMPLETE")
print("=" * 80)


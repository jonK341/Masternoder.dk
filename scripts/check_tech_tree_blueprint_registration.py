#!/usr/bin/env python3
"""
Check Tech Tree Blueprint Registration
Verifies if tech_tree blueprint is registered and routes are available
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_registration():
    """Check blueprint registration"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html/vidgenerator")

from src.app import create_app

app = create_app()

# Check for tech_tree blueprint
print("="*70)
print("CHECKING TECH_TREE BLUEPRINT")
print("="*70)

blueprints = list(app.blueprints.keys())
if 'tech_tree' in blueprints:
    print("  ✅ tech_tree blueprint IS registered")
else:
    print("  ❌ tech_tree blueprint NOT registered")
    print(f"  Available blueprints: {sorted(blueprints)}")

# Check for routes with 'knowledge'
print()
print("="*70)
print("CHECKING KNOWLEDGE ROUTES")
print("="*70)
routes_with_knowledge = [str(r) for r in app.url_map.iter_rules() if 'knowledge' in str(r)]
if routes_with_knowledge:
    print(f"  ✅ Found {len(routes_with_knowledge)} routes with 'knowledge':")
    for r in routes_with_knowledge:
        print(f"      {r}")
else:
    print("  ❌ No routes with 'knowledge' found")

# Check for routes with 'tech-tree'
print()
print("="*70)
print("CHECKING TECH-TREE ROUTES")
print("="*70)
routes_with_tech_tree = [str(r) for r in app.url_map.iter_rules() if 'tech-tree' in str(r)]
if routes_with_tech_tree:
    print(f"  ✅ Found {len(routes_with_tech_tree)} routes with 'tech-tree':")
    for r in routes_with_tech_tree[:10]:  # Show first 10
        print(f"      {r}")
    if len(routes_with_tech_tree) > 10:
        print(f"      ... and {len(routes_with_tech_tree) - 10} more")
else:
    print("  ❌ No routes with 'tech-tree' found")

# Check tech_tree_routes.py file
print()
print("="*70)
print("CHECKING TECH_TREE_ROUTES.PY FILE")
print("="*70)
import os
tech_tree_file = '/var/www/html/vidgenerator/backend/routes/tech_tree_routes.py'
if os.path.exists(tech_tree_file):
    print(f"  ✅ File exists: {tech_tree_file}")
    with open(tech_tree_file, 'r') as f:
        content = f.read()
        if 'def get_knowledge' in content:
            print("  ✅ get_knowledge function exists")
        else:
            print("  ❌ get_knowledge function NOT found")
        if '@tech_tree_bp.route' in content and 'knowledge' in content:
            print("  ✅ Route decorator with 'knowledge' exists")
        else:
            print("  ❌ Route decorator with 'knowledge' NOT found")
else:
    print(f"  ❌ File NOT found: {tech_tree_file}")

# Check register_blueprints.py
print()
print("="*70)
print("CHECKING REGISTER_BLUEPRINTS.PY")
print("="*70)
register_file = '/var/www/html/vidgenerator/backend/register_blueprints.py'
if os.path.exists(register_file):
    print(f"  ✅ File exists: {register_file}")
    with open(register_file, 'r') as f:
        content = f.read()
        if 'tech_tree' in content and 'register' in content.lower():
            print("  ✅ tech_tree blueprint registration code exists")
            # Find the line
            for i, line in enumerate(content.split('\\n'), 1):
                if 'tech_tree' in line and ('register' in line.lower() or 'blueprint' in line.lower()):
                    print(f"      Line {i}: {line.strip()}")
        else:
            print("  ❌ tech_tree blueprint registration code NOT found")
else:
    print(f"  ❌ File NOT found: {register_file}")
'''
        
        print("[1/1] Running registration check...")
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=120
        )
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if output:
            print(output)
        if error:
            print()
            print("ERRORS:")
            print(error)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_registration()

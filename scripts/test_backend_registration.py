#!/usr/bin/env python3
"""
Test if backend blueprints are registered when app starts
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def test_registration():
    """Test backend blueprint registration"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        
        print("=" * 60)
        print("Testing backend blueprint registration")
        print("=" * 60)
        print()
        
        # Test if blueprints are registered
        cmd = """cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 -c "
import sys
sys.stdout.flush()

from src.app import create_app
app = create_app()

# Check for backend registration messages
print('\\n=== Checking for backend blueprints ===')

# Check if backend blueprints are registered
backend_bps = ['gallery', 'generator', 'game']
found = []
for bp_name in backend_bps:
    if bp_name in app.blueprints:
        found.append(bp_name)
        print(f'✅ Found blueprint: {bp_name}')
    else:
        print(f'❌ Missing blueprint: {bp_name}')

print(f'\\nFound {len(found)}/{len(backend_bps)} backend blueprints')

# Check routes
print('\\n=== Checking routes ===')
target_routes = [
    '/api/gallery/list',
    '/api/generator/create', 
    '/api/game/xp',
    '/api/debug/errors/scan'
]

for target in target_routes:
    found_route = False
    for rule in app.url_map.iter_rules():
        if target in rule.rule:
            print(f'✅ Found route: {rule.rule} {list(rule.methods)}')
            found_route = True
            break
    if not found_route:
        print(f'❌ Missing route: {target}')
" 2>&1 | grep -A 50 'Checking for backend'"""
        
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        print(output)
        if error:
            print("\nErrors:")
            print(error[-1000:])
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    test_registration()

import os

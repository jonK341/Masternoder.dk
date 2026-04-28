#!/usr/bin/env python3
"""
Check if backend blueprints are actually being registered
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def check_registration():
    """Check blueprint registration"""
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
        print("Checking blueprint registration on server")
        print("=" * 60)
        print()
        
        # Check if blueprints are being registered
        cmd = """cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 -c "
from src.app import create_app
app = create_app()

# Check for backend blueprint registration messages
import sys
sys.stdout.flush()

# Get all routes
routes = list(app.url_map.iter_rules())
api_routes = [r for r in routes if '/api/' in r.rule]

# Check for specific routes
target_routes = ['/api/gallery/list', '/api/generator/create', '/api/game/xp', '/api/debug/errors/scan']
found = []
for route in api_routes:
    for target in target_routes:
        if target in route.rule:
            found.append(f'{route.rule} {list(route.methods)}')
            break

print(f'Found {len(found)} target routes:')
for f in found:
    print(f'  {f}')

# Check blueprint endpoints
blueprints = list(app.blueprints.keys())
print(f'\\nRegistered blueprints: {len(blueprints)}')
for bp in sorted(blueprints):
    if 'gallery' in bp.lower() or 'generator' in bp.lower() or 'game' in bp.lower():
        print(f'  - {bp}')
" 2>&1"""
        
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        print("Registration check:")
        print(output)
        if error and "Traceback" in error:
            print("\nErrors:")
            print(error[-1000:])
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    check_registration()

import os

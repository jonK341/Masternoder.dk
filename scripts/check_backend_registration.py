#!/usr/bin/env python3
"""
Check if backend.register_blueprints is being called
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def check_backend():
    """Check backend blueprint registration"""
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
        print("Checking backend blueprint registration")
        print("=" * 60)
        print()
        
        # Check if register_all_blueprints is being called
        cmd = """cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 -c "
import sys
sys.stdout.flush()

# Try importing
try:
    from backend.register_blueprints import register_all_blueprints
    print('✅ Successfully imported register_all_blueprints')
except Exception as e:
    print(f'❌ Import error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Try importing blueprints
try:
    from backend.routes.generator import generator_bp
    print('✅ Successfully imported generator_bp')
except Exception as e:
    print(f'❌ Generator import error: {e}')

try:
    from backend.routes.gallery import gallery_bp
    print('✅ Successfully imported gallery_bp')
except Exception as e:
    print(f'❌ Gallery import error: {e}')

try:
    from backend.routes.game import game_bp
    print('✅ Successfully imported game_bp')
except Exception as e:
    print(f'❌ Game import error: {e}')

# Check routes in blueprints
try:
    from backend.routes.generator import generator_bp
    routes = list(generator_bp.deferred_functions)
    print(f'\\nGenerator blueprint has {len(routes)} deferred functions')
    for route in generator_bp.url_map.iter_rules():
        print(f'  Route: {route.rule} {list(route.methods)}')
except Exception as e:
    print(f'Error checking generator routes: {e}')
" 2>&1"""
        
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        print(output)
        if error and "Traceback" in error:
            print("\nErrors:")
            print(error[-1500:])
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    check_backend()

import os

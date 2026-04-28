#!/usr/bin/env python3
"""
Test backend import on server
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def test_import():
    """Test backend import"""
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
        print("Testing backend import on server")
        print("=" * 60)
        print()
        
        cmd = """cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 -c "
import sys
sys.stdout.flush()

print('Testing import...')
try:
    from backend.register_blueprints import register_all_blueprints
    print('✅ Import successful')
except ImportError as e:
    print(f'❌ ImportError: {e}')
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f'❌ Other error: {e}')
    import traceback
    traceback.print_exc()

print('\\nTesting function call...')
try:
    from flask import Flask
    app = Flask(__name__)
    from backend.register_blueprints import register_all_blueprints
    register_all_blueprints(app)
    print('✅ Function call successful')
    print(f'Registered blueprints: {list(app.blueprints.keys())}')
except Exception as e:
    print(f'❌ Error calling function: {e}')
    import traceback
    traceback.print_exc()
" 2>&1"""
        
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        print(output)
        if error:
            print("\nStderr:")
            print(error[-2000:])
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    test_import()

import os

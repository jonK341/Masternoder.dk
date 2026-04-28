#!/usr/bin/env python3
"""
Check if backend registration happens in create_app
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def check_app():
    """Check app creation"""
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
        print("Checking backend registration in create_app")
        print("=" * 60)
        print()
        
        cmd = """cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 << 'PYTHON_SCRIPT'
import sys
sys.stdout.flush()

# Monkey patch to capture exceptions
original_print = print
def debug_print(*args, **kwargs):
    original_print(*args, **kwargs)
    sys.stdout.flush()

print = debug_print

# Capture all output
output_lines = []
class Tee:
    def __init__(self):
        self.original = sys.stdout
    def write(self, s):
        self.original.write(s)
        output_lines.append(s)
    def flush(self):
        self.original.flush()

tee = Tee()
sys.stdout = tee

try:
    print('Creating app...')
    from src.app import create_app
    app = create_app()
    
    print(f'\\nApp created. Blueprints: {len(app.blueprints)}')
    
    # Check for backend blueprints
    backend_bps = ['generator', 'gallery', 'game']
    for bp_name in backend_bps:
        if bp_name in app.blueprints:
            print(f'✅ Found: {bp_name}')
        else:
            print(f'❌ Missing: {bp_name}')
    
    # Check output for backend messages
    output = ''.join(output_lines)
    if '[Backend]' in output:
        print('\\n=== Backend messages found ===')
        for line in output.split('\\n'):
            if '[Backend]' in line or 'Registered' in line and 'blueprint' in line.lower():
                print(line)
    else:
        print('\\n❌ NO backend registration messages!')
        print('This means register_all_blueprints was NOT called or failed silently')
        
except Exception as e:
    print(f'\\n❌ Error: {e}')
    import traceback
    traceback.print_exc()

PYTHON_SCRIPT
"""
        
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        print(output)
        if error and "Traceback" in error:
            print("\nErrors:")
            print(error[-2000:])
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    check_app()

import os

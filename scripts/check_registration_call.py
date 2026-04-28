#!/usr/bin/env python3
"""
Check if register_all_blueprints is being called and if there are errors
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def check_call():
    """Check if registration function is called"""
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
        print("Checking backend blueprint registration call")
        print("=" * 60)
        print()
        
        # Check if register_all_blueprints is being called
        cmd = """cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 -c "
import sys
sys.stdout.flush()

# Capture print statements
class Tee:
    def __init__(self):
        self.lines = []
    def write(self, s):
        self.lines.append(s)
        sys.__stdout__.write(s)
    def flush(self):
        sys.__stdout__.flush()

tee = Tee()
sys.stdout = tee

try:
    from src.app import create_app
    app = create_app()
    
    # Check output for backend registration
    output = ''.join(tee.lines)
    if '[Backend]' in output:
        print('\\n=== Backend registration messages ===')
        for line in output.split('\\n'):
            if '[Backend]' in line or 'Registered' in line or 'blueprint' in line.lower():
                print(line)
    else:
        print('❌ No backend registration messages found!')
        
    # Check for errors
    if 'ERROR' in output or 'Error' in output:
        print('\\n=== Errors found ===')
        for line in output.split('\\n'):
            if 'ERROR' in line or 'Error' in line or 'Traceback' in line:
                print(line)
                
except Exception as e:
    print(f'❌ Error creating app: {e}')
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
    check_call()

import os

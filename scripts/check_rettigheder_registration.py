#!/usr/bin/env python3
"""
Check if rettigheder blueprint is registered on server
"""

import paramiko

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
        
        print("=" * 70)
        print("Checking Rettigheder Blueprint Registration")
        print("=" * 70)
        print()
        
        # Check if file exists
        cmd = "test -f /var/www/html/vidgenerator/backend/routes/rettigheder.py && echo 'EXISTS' || echo 'MISSING'"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        file_status = stdout.read().decode().strip()
        print(f"Rettigheder file: {file_status}")
        
        # Check if registered in register_blueprints.py
        cmd2 = "grep -n 'rettigheder' /var/www/html/vidgenerator/backend/register_blueprints.py | head -5"
        stdin2, stdout2, stderr2 = ssh_client.exec_command(cmd2)
        registration_code = stdout2.read().decode()
        
        if registration_code:
            print("\n✅ Found registration code:")
            print(registration_code)
        else:
            print("\n❌ Registration code NOT FOUND!")
        
        # Test if blueprint can be imported
        cmd3 = """cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/var/www/html/vidgenerator')

try:
    from backend.routes.rettigheder import rettigheder_bp
    print("✅ Blueprint can be imported")
    print(f"   Blueprint name: {rettigheder_bp.name}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
PYTHON_SCRIPT"""
        
        stdin3, stdout3, stderr3 = ssh_client.exec_command(cmd3)
        output3 = stdout3.read().decode()
        error3 = stderr3.read().decode()
        
        print("\nImport test:")
        print(output3)
        if error3:
            print("Errors:")
            print(error3)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    check_registration()

import os

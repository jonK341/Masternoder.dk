#!/usr/bin/env python3
"""
Check if backend registration is actually being called in create_app
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def check_import():
    """Check if backend registration is called"""
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
        print("Checking if backend registration code exists in src/app.py")
        print("=" * 70)
        print()
        
        # Check if the code exists
        cmd = "grep -A 10 'Register Micro integration blueprints' /var/www/html/vidgenerator/src/app.py"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        
        if output:
            print("Found backend registration code:")
            print(output)
        else:
            print("❌ Backend registration code NOT FOUND in src/app.py!")
            print("This explains why it's not being called!")
        
        # Check for the print statements
        cmd2 = "grep -E 'Calling register_all_blueprints|Backend blueprints registration completed' /var/www/html/vidgenerator/src/app.py"
        stdin2, stdout2, stderr2 = ssh_client.exec_command(cmd2)
        output2 = stdout2.read().decode()
        
        if output2:
            print("\nFound debug print statements:")
            print(output2)
        else:
            print("\n❌ Debug print statements NOT FOUND!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    check_import()


import os

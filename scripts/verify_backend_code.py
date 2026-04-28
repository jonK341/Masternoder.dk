#!/usr/bin/env python3
"""
Verify backend registration code exists in src/app.py on server
"""

import paramiko

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def verify_code():
    """Verify backend code exists"""
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
        print("Verifying backend registration code in src/app.py")
        print("=" * 70)
        print()
        
        # Check for the key lines
        cmd = "grep -n 'register_all_blueprints' /var/www/html/vidgenerator/src/app.py"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        
        if output:
            print("✅ Found register_all_blueprints call:")
            print(output)
        else:
            print("❌ register_all_blueprints NOT FOUND!")
        
        print()
        
        # Check for the import
        cmd2 = "grep -n 'from backend.register_blueprints import' /var/www/html/vidgenerator/src/app.py"
        stdin2, stdout2, stderr2 = ssh_client.exec_command(cmd2)
        output2 = stdout2.read().decode()
        
        if output2:
            print("✅ Found import statement:")
            print(output2)
        else:
            print("❌ Import statement NOT FOUND!")
        
        print()
        
        # Show the relevant section
        cmd3 = "sed -n '220,250p' /var/www/html/vidgenerator/src/app.py"
        stdin3, stdout3, stderr3 = ssh_client.exec_command(cmd3)
        output3 = stdout3.read().decode()
        
        print("Lines 220-250 of src/app.py:")
        print("-" * 70)
        print(output3)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    verify_code()

import os

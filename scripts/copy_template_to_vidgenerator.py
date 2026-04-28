#!/usr/bin/env python3
"""
Copy api_debugger.html template to vidgenerator/templates
"""

import paramiko

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def copy_template():
    """Copy template"""
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
        print("Copying Template to vidgenerator/templates")
        print("=" * 60)
        print()
        
        # Create directory if needed
        cmd1 = "mkdir -p /var/www/html/vidgenerator/vidgenerator/templates"
        stdin1, stdout1, stderr1 = ssh_client.exec_command(cmd1)
        stdout1.channel.recv_exit_status()
        
        # Copy template to vidgenerator root (Flask uses vidgenerator as template folder, not vidgenerator/templates)
        cmd2 = "cp /var/www/html/vidgenerator/backend/templates/api_debugger.html /var/www/html/vidgenerator/vidgenerator/api_debugger.html"
        stdin2, stdout2, stderr2 = ssh_client.exec_command(cmd2)
        exit_code = stdout2.channel.recv_exit_status()
        
        if exit_code == 0:
            print("✅ Template copied successfully!")
        else:
            error = stderr2.read().decode()
            print(f"❌ Error: {error}")
        
        # Verify
        cmd3 = "test -f /var/www/html/vidgenerator/vidgenerator/api_debugger.html && echo 'EXISTS' || echo 'MISSING'"
        stdin3, stdout3, stderr3 = ssh_client.exec_command(cmd3)
        status = stdout3.read().decode().strip()
        print(f"Template status: {status}")
        
        if status == "EXISTS":
            # Check content
            cmd4 = "grep -c 'Rettigheder' /var/www/html/vidgenerator/vidgenerator/api_debugger.html"
            stdin4, stdout4, stderr4 = ssh_client.exec_command(cmd4)
            count = stdout4.read().decode().strip()
            print(f"Contains 'Rettigheder': {count} times")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    copy_template()

import os

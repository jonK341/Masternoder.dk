#!/usr/bin/env python3
"""
Check if api_debugger.html template exists and is accessible
"""

import paramiko

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def check_template():
    """Check template location"""
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
        print("Checking Template Location")
        print("=" * 70)
        print()
        
        # Check if template exists
        template_paths = [
            "/var/www/html/vidgenerator/backend/templates/api_debugger.html",
            "/var/www/html/vidgenerator/vidgenerator/templates/api_debugger.html",
        ]
        
        for path in template_paths:
            cmd = f"test -f {path} && echo 'EXISTS' || echo 'MISSING'"
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            status = stdout.read().decode().strip()
            print(f"{path}: {status}")
            
            if status == "EXISTS":
                # Check file size
                cmd2 = f"wc -l {path}"
                stdin2, stdout2, stderr2 = ssh_client.exec_command(cmd2)
                lines = stdout2.read().decode().strip()
                print(f"  → {lines} lines")
                
                # Check for key content
                cmd3 = f"grep -c 'Rettigheder' {path}"
                stdin3, stdout3, stderr3 = ssh_client.exec_command(cmd3)
                count = stdout3.read().decode().strip()
                print(f"  → Contains 'Rettigheder': {count} times")
        
        print()
        
        # Check Flask template search paths
        cmd4 = """cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/var/www/html/vidgenerator')

from flask import Flask
from src.app import create_app

app = create_app()

print("Flask template search paths:")
for path in app.jinja_env.loader.searchpath:
    print(f"  {path}")
PYTHON_SCRIPT"""
        
        stdin4, stdout4, stderr4 = ssh_client.exec_command(cmd4)
        output4 = stdout4.read().decode()
        print("Template search paths:")
        print(output4)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    check_template()

import os

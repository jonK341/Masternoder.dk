#!/usr/bin/env python3
"""
Check if backend blueprints are registered on server
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def check_blueprints():
    """Check blueprint registration on server"""
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
        print("Checking backend blueprint registration on server")
        print("=" * 60)
        print()
        
        # Check if backend/register_blueprints.py exists and has the fix
        cmd = "cd /var/www/html/vidgenerator && grep -n 'No url_prefix' backend/register_blueprints.py | head -5"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        
        if output:
            print("✅ Fix found in backend/register_blueprints.py:")
            print(output)
        else:
            print("❌ Fix NOT found in file!")
            print("Checking file content...")
            cmd2 = "cd /var/www/html/vidgenerator && grep -A 2 'generator_bp' backend/register_blueprints.py | head -10"
            stdin2, stdout2, stderr2 = ssh_client.exec_command(cmd2)
            print(stdout2.read().decode())
        
        print()
        
        # Check if blueprints are being registered
        cmd3 = "cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 -c \"from src.app import create_app; app = create_app(); routes = [r for r in app.url_map.iter_rules() if '/api/gallery/list' in r.rule or '/api/generator/create' in r.rule or '/api/game/xp' in r.rule]; print('Found', len(routes), 'backend API routes:'); [print(f'  {r.rule} [{list(r.methods)}]') for r in routes]\" 2>&1 | tail -30"
        stdin3, stdout3, stderr3 = ssh_client.exec_command(cmd3)
        output3 = stdout3.read().decode()
        error3 = stderr3.read().decode()
        
        print("Backend API routes on server:")
        print(output3)
        if error3 and "Traceback" in error3:
            print("Errors:")
            print(error3[-500:])  # Last 500 chars
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    check_blueprints()

import os

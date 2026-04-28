#!/usr/bin/env python3
"""
Compare Both App Files
Compares the two app.py files to see differences
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def compare_apps():
    """Compare both app files"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        app_paths = {
            "Main app": "/var/www/html/src/app.py",
            "Vidgenerator app": "/var/www/html/vidgenerator/src/app.py"
        }
        
        for name, path in app_paths.items():
            print(f"="*70)
            print(f"{name}: {path}")
            print("="*70)
            
            # Check file size and modification time
            stdin, stdout, stderr = ssh.exec_command(f"stat -c '%s %y' {path} 2>/dev/null || stat -f '%z %Sm' {path}", timeout=5)
            stat_info = stdout.read().decode().strip()
            print(f"File info: {stat_info}")
            
            # Check if create_app function exists
            stdin2, stdout2, stderr2 = ssh.exec_command(f"grep -n 'def create_app' {path} | head -1", timeout=5)
            create_app_line = stdout2.read().decode().strip()
            if create_app_line:
                print(f"create_app function: {create_app_line}")
            
            # Check for register_blueprints call
            stdin3, stdout3, stderr3 = ssh.exec_command(f"grep -n 'register.*blueprint' {path} | head -3", timeout=5)
            blueprint_calls = stdout3.read().decode().strip()
            if blueprint_calls:
                print(f"Blueprint registration calls:")
                print(blueprint_calls)
            
            print()
        
        # Check which one wsgi.py imports
        print("="*70)
        print("WSGI.py imports:")
        print("="*70)
        stdin4, stdout4, stderr4 = ssh.exec_command("grep -n 'from.*app import' /var/www/html/vidgenerator/wsgi.py | head -3", timeout=5)
        wsgi_imports = stdout4.read().decode().strip()
        print(wsgi_imports)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    compare_apps()

#!/usr/bin/env python3
"""
Check Server App Structure
Check where src/app/__init__.py should be located on the server
"""
import paramiko
import os

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def check_structure():
    """Check server structure"""
    print("=" * 70)
    print("CHECKING SERVER APP STRUCTURE")
    print("=" * 70)
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        # Check possible locations
        paths_to_check = [
            '/var/www/html/src/app/__init__.py',
            '/var/www/html/vidgenerator/src/app/__init__.py',
            '/var/www/html/app/__init__.py',
            '/var/www/html/vidgenerator/app/__init__.py',
        ]
        
        print("[1/3] Checking for existing app/__init__.py files...")
        for path in paths_to_check:
            cmd = f"test -f {path} && echo 'EXISTS' || echo 'NOT FOUND'"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            result = stdout.read().decode('utf-8').strip()
            if result == 'EXISTS':
                print(f"  [OK] Found: {path}")
            else:
                print(f"  [ ] Not found: {path}")
        
        print()
        print("[2/3] Checking directory structure...")
        dirs_to_check = [
            '/var/www/html/src',
            '/var/www/html/src/app',
            '/var/www/html/vidgenerator/src',
            '/var/www/html/vidgenerator/src/app',
            '/var/www/html/backend',
        ]
        
        for dir_path in dirs_to_check:
            cmd = f"test -d {dir_path} && echo 'EXISTS' || echo 'NOT FOUND'"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            result = stdout.read().decode('utf-8').strip()
            if result == 'EXISTS':
                print(f"  [OK] Directory exists: {dir_path}")
            else:
                print(f"  [ ] Directory missing: {dir_path}")
        
        print()
        print("[3/3] Checking wsgi.py location...")
        wsgi_paths = [
            '/var/www/html/wsgi.py',
            '/var/www/html/vidgenerator/wsgi.py',
        ]
        
        for path in wsgi_paths:
            cmd = f"test -f {path} && echo 'EXISTS' || echo 'NOT FOUND'"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            result = stdout.read().decode('utf-8').strip()
            if result == 'EXISTS':
                print(f"  [OK] Found wsgi.py: {path}")
                # Check what it imports
                cmd2 = f"grep -E 'from.*app.*import|import.*app' {path} 2>/dev/null | head -3"
                stdin, stdout, stderr = ssh.exec_command(cmd2, timeout=10)
                imports = stdout.read().decode('utf-8').strip()
                if imports:
                    print(f"    Imports: {imports}")
        
        print()
        print("=" * 70)
        print("RECOMMENDATION")
        print("=" * 70)
        print()
        print("Based on the auto-fix deployment script:")
        print("  SERVER_BASE = '/var/www/html'")
        print()
        print("The src/app/__init__.py file should be uploaded to:")
        print("  /var/www/html/src/app/__init__.py")
        print()
        print("This matches the structure:")
        print("  /var/www/html/")
        print("    ├── backend/")
        print("    │   ├── services/")
        print("    │   ├── middleware/")
        print("    │   └── routes/")
        print("    └── src/")
        print("        └── app/")
        print("            └── __init__.py  <-- Upload here")
        
        ssh.close()
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_structure()

#!/usr/bin/env python3
"""
Fix Static File Paths
Checks and fixes static file paths in nginx config
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_static_paths():
    """Fix static file paths"""
    print("="*70)
    print("FIXING STATIC FILE PATHS")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Check where static files actually are
        print("[1/3] Checking static file locations...")
        static_locations = [
            "/var/www/html/vidgenerator/static",
            "/var/www/html/vidgenerator/src/web/static",
            "/var/www/html/vidgenerator/static/css",
            "/var/www/html/vidgenerator/static/js",
        ]
        
        for location in static_locations:
            stdin, stdout, stderr = ssh.exec_command(f"test -d {location} && echo 'EXISTS' || echo 'MISSING'", timeout=5)
            result = stdout.read().decode().strip()
            if result == 'EXISTS':
                # Count files
                stdin2, stdout2, stderr2 = ssh.exec_command(f"find {location} -type f 2>/dev/null | wc -l", timeout=5)
                file_count = stdout2.read().decode().strip()
                print(f"  [OK] {location} - {file_count} files")
            else:
                print(f"  [INFO] {location} - does not exist")
        print()
        
        # Check nginx config
        print("[2/3] Checking nginx static file configuration...")
        try:
            stdin, stdout, stderr = ssh.exec_command("grep -A 5 'location /vidgenerator/static' /etc/nginx/sites-enabled/masternoder.dk", timeout=10)
            output = stdout.read().decode().strip()
            if output:
                print("  Current nginx config:")
                for line in output.split('\n'):
                    print(f"    {line}")
        except Exception as e:
            print(f"  [ERROR] {e}")
        print()
        
        # Suggest fix
        print("[3/3] Suggested fix:")
        print("  Update nginx config to point to:")
        print("    /var/www/html/vidgenerator/static")
        print("  Instead of:")
        print("    /var/www/html/vidgenerator/src/web/static")
        print()
        
        # Check if we should update nginx config
        print("Would you like to update nginx config? (This requires root access)")
        print("  The fix would change:")
        print("    alias /var/www/html/vidgenerator/src/web/static;")
        print("  To:")
        print("    alias /var/www/html/vidgenerator/static;")
        print()
        
        print("="*70)
        print("STATIC FILE PATH CHECK COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_static_paths()

#!/usr/bin/env python3
"""
Cleanup and Test Nginx
Removes backup files and tests nginx
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def cleanup_and_test():
    """Cleanup and test"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Remove backup files
        print("[1/2] Removing backup files...")
        stdin, stdout, stderr = ssh.exec_command(
            "rm -f /etc/nginx/sites-enabled/*.backup.*",
            timeout=10
        )
        stdout.read()
        print("  [OK] Backup files removed")
        
        # Test nginx
        print()
        print("[2/2] Testing nginx configuration...")
        stdin2, stdout2, stderr2 = ssh.exec_command("nginx -t 2>&1", timeout=10)
        output = stdout2.read().decode().strip()
        error = stderr2.read().decode().strip()
        
        print(output)
        if error:
            print(error)
        
        if "syntax is ok" in output or "syntax is ok" in error:
            print()
            print("  [OK] Nginx config is valid!")
            
            # Reload nginx
            print()
            print("Reloading nginx...")
            stdin3, stdout3, stderr3 = ssh.exec_command("systemctl reload nginx", timeout=10)
            stdout3.read()
            print("  [OK] Nginx reloaded")
        else:
            print()
            print("  [ERROR] Nginx config test failed")
            return False
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    cleanup_and_test()

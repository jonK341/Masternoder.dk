#!/usr/bin/env python3
"""
Check Nginx and uWSGI Configuration
Checks nginx config and uwsgi status
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_config():
    """Check nginx and uwsgi config"""
    print("="*70)
    print("CHECKING NGINX AND UWSGI CONFIGURATION")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Check uwsgi status
        print("[1/4] Checking uwsgi status...")
        try:
            stdin, stdout, stderr = ssh.exec_command("systemctl status uwsgi-vidgenerator --no-pager | head -10", timeout=10)
            output = stdout.read().decode().strip()
            if output:
                for line in output.split('\n')[:10]:
                    print(f"  {line}")
        except Exception as e:
            print(f"  [ERROR] {e}")
        print()
        
        # Check nginx config for vidgenerator
        print("[2/4] Checking nginx configuration...")
        try:
            stdin, stdout, stderr = ssh.exec_command("grep -A 20 'location /vidgenerator' /etc/nginx/sites-enabled/* 2>&1 | head -30", timeout=10)
            output = stdout.read().decode().strip()
            if output:
                for line in output.split('\n'):
                    print(f"  {line}")
            else:
                print("  [WARN] Could not find nginx config for /vidgenerator")
        except Exception as e:
            print(f"  [ERROR] {e}")
        print()
        
        # Check if nginx needs reload
        print("[3/4] Testing nginx configuration...")
        try:
            stdin, stdout, stderr = ssh.exec_command("nginx -t 2>&1", timeout=10)
            output = stdout.read().decode().strip()
            if output:
                for line in output.split('\n'):
                    print(f"  {line}")
        except Exception as e:
            print(f"  [ERROR] {e}")
        print()
        
        # Check uwsgi socket
        print("[4/4] Checking uwsgi socket...")
        socket_paths = [
            "/run/uwsgi/app/vidgenerator/socket",
            "/var/run/uwsgi/app/vidgenerator/socket",
            "/tmp/uwsgi-vidgenerator.sock",
        ]
        
        for socket_path in socket_paths:
            try:
                stdin, stdout, stderr = ssh.exec_command(f"test -S {socket_path} && echo 'EXISTS' || echo 'MISSING'", timeout=5)
                result = stdout.read().decode().strip()
                if result == 'EXISTS':
                    print(f"  [OK] Socket found: {socket_path}")
                else:
                    print(f"  [INFO] Socket not found: {socket_path}")
            except Exception as e:
                pass
        
        print()
        print("="*70)
        print("CONFIGURATION CHECK COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_config()

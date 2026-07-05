"""
Restart all production services after deployment
"""
import os
import sys
import paramiko
import time

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def restart_production_services():
    """Restart all production services"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("RESTARTING PRODUCTION SERVICES")
        print("=" * 80)
        print(f"Connecting to {SERVER_HOST}...")
        
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        
        print("[OK] Connected!")
        print()
        
        # Clear Python cache
        print("[CLEAR] Python cache...")
        commands = [
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -r {} + 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyo' -delete 2>/dev/null || true",
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("[OK] Cache cleared")
        print()
        
        # Restart services
        services = [
            ("python-proxy.service", "Flask Application"),
            ("uwsgi", "uWSGI"),
            ("nginx", "Nginx"),
        ]
        
        for service, name in services:
            print(f"[RESTART] {name}...")
            try:
                if service == "uwsgi":
                    # Restart uWSGI
                    cmd = "systemctl restart uwsgi 2>&1 || service uwsgi restart 2>&1 || true"
                elif service == "nginx":
                    # Restart nginx
                    cmd = "systemctl restart nginx 2>&1 || service nginx restart 2>&1 || true"
                else:
                    # Restart systemd service
                    cmd = f"systemctl restart {service} 2>&1"
                
                stdin, stdout, stderr = ssh_client.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                output = stdout.read().decode('utf-8', errors='ignore')
                error_output = stderr.read().decode('utf-8', errors='ignore')
                
                if exit_status == 0:
                    print(f"[OK] {name} restarted")
                else:
                    print(f"[WARN] {name} restart status: {exit_status}")
                    if output:
                        print(f"   Output: {output[:200]}")
                    if error_output:
                        print(f"   Error: {error_output[:200]}")
                
                # Check service status
                if service.endswith('.service'):
                    status_cmd = f"systemctl is-active {service} 2>&1"
                    stdin, stdout, stderr = ssh_client.exec_command(status_cmd)
                    status = stdout.read().decode('utf-8', errors='ignore').strip()
                    if status == 'active':
                        print(f"[OK] {name} is active")
                    else:
                        print(f"[WARN] {name} status: {status}")
                
            except Exception as e:
                print(f"[WARN] Error restarting {name}: {e}")
            
            time.sleep(1)  # Small delay between restarts
        
        print()
        print("=" * 80)
        print("[OK] All services restarted!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh_client.close()

if __name__ == '__main__':
    success = restart_production_services()
    sys.exit(0 if success else 1)


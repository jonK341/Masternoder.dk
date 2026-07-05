"""
Restart services and clear cache for enhanced stats deployment
"""
import paramiko
import os

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def restart_services():
    """Clear cache and restart services"""
    try:
        print("=" * 70)
        print("RESTARTING SERVICES FOR ENHANCED STATS")
        print("=" * 70)
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        print("[OK] Connected to server")
        print()
        
        # Clear Python cache
        print("Clearing Python cache...")
        print("-" * 70)
        commands = [
            'find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true',
            'find /var/www/html -name "*.pyc" -delete 2>/dev/null || true',
        ]
        
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        
        print("[OK] Python cache cleared")
        print()
        
        # Restart services
        print("Restarting services...")
        print("-" * 70)
        
        services = [
            'python-proxy.service',
            'uwsgi',
        ]
        
        for service in services:
            try:
                print(f"Restarting {service}...")
                stdin, stdout, stderr = ssh.exec_command(f'sudo systemctl restart {service}')
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    print(f"[OK] {service} restarted")
                else:
                    error = stderr.read().decode()
                    print(f"[WARN] {service} restart may have issues: {error[:100]}")
            except Exception as e:
                print(f"[WARN] Could not restart {service}: {e}")
        
        print()
        print("=" * 70)
        print("[OK] Service restart complete!")
        print("=" * 70)
        print()
        print("Wait 10-15 seconds for services to fully restart, then test endpoints.")
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    restart_services()


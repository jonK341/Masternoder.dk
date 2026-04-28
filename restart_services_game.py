"""Restart services after game deployment"""
import os
import sys
import paramiko
import time

DEPLOY_HOST = 'masternoder.dk'
DEPLOY_USER = os.getenv('DEPLOY_USER', 'root')
DEPLOY_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def restart_services():
    """Restart all services"""
    try:
        print("=" * 70)
        print("Restarting Services")
        print("=" * 70)
        print()
        
        # Connect to server
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(DEPLOY_HOST, username=DEPLOY_USER, password=DEPLOY_PASS)
        
        # Clear Python cache
        print("[CLEAR] Python cache...")
        ssh.exec_command('find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true')
        ssh.exec_command('find /var/www/html -type f -name "*.pyc" -delete 2>/dev/null || true')
        
        # Restart python-proxy service
        print("[RESTART] python-proxy.service...")
        stdin, stdout, stderr = ssh.exec_command('systemctl restart python-proxy.service')
        time.sleep(2)
        stdin, stdout, stderr = ssh.exec_command('systemctl status python-proxy.service --no-pager')
        status = stdout.read().decode()
        if 'active (running)' in status:
            print("[OK] python-proxy.service is active")
        else:
            print("[WARN] python-proxy.service status unclear")
        
        # Restart uWSGI
        print("[RESTART] uWSGI...")
        ssh.exec_command('systemctl restart uwsgi 2>/dev/null || true')
        time.sleep(1)
        
        # Restart nginx
        print("[RESTART] nginx...")
        stdin, stdout, stderr = ssh.exec_command('systemctl restart nginx')
        time.sleep(1)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("[OK] nginx restarted")
        else:
            print(f"[WARN] nginx restart status: {exit_status}")
        
        ssh.close()
        
        print()
        print("=" * 70)
        print("[OK] All services restarted!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Restart failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = restart_services()
    sys.exit(0 if success else 1)


#!/usr/bin/env python3
"""
Simple route test
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def test():
    """Test routes"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("SIMPLE ROUTE TEST")
        print("=" * 80)
        print()
        
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        # Make a request and immediately check logs
        print("📋 Making request and checking logs...")
        print("-" * 80)
        cmd = """
curl -s http://127.0.0.1:5000/api/activity-points/leaderboard > /dev/null 2>&1
sleep 1
tail -100 /var/log/uwsgi/vidgenerator.log | tail -30
"""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode('utf-8', errors='ignore')
        print(output)
        
        # Check if we can import the route
        print()
        print("📋 Testing import...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 -c 'from backend.routes.activity_points_routes import activity_points_bp; print(\"Import OK\")' 2>&1")
        import_test = stdout.read().decode('utf-8', errors='ignore')
        print(import_test)
        if stderr:
            err = stderr.read().decode('utf-8', errors='ignore')
            if err:
                print(f"STDERR: {err}")
        
        ssh.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test()


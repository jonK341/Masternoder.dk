#!/usr/bin/env python3
"""
Get actual error from Battle Intelligence endpoints
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def get_error():
    """Get actual error from endpoints"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("GETTING ACTUAL ERRORS FROM ENDPOINTS")
        print("=" * 80)
        print()
        
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        # Test activity points endpoint with full response
        print("📋 Testing Activity Points Leaderboard...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:5000/api/activity-points/leaderboard")
        response1 = stdout.read().decode('utf-8', errors='ignore')
        print(response1)
        
        print()
        print("📋 Testing Battle Intelligence Quick...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("curl -s 'http://127.0.0.1:5000/api/battle/intelligence/mode/quick?user_id=test'")
        response2 = stdout.read().decode('utf-8', errors='ignore')
        print(response2)
        
        print()
        print("📋 Checking recent uWSGI errors...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("tail -200 /var/log/uwsgi/vidgenerator.log | tail -50")
        recent_logs = stdout.read().decode('utf-8', errors='ignore')
        print(recent_logs)
        
        ssh.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    get_error()


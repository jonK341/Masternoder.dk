#!/usr/bin/env python3
"""
Get detailed error traceback
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def get_detailed_error():
    """Get detailed error traceback"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("GETTING DETAILED ERROR TRACEBACK")
        print("=" * 80)
        print()
        
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        # Get full uWSGI log
        print("📋 Full uWSGI error log (last 100 lines)...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("tail -100 /var/log/uwsgi/vidgenerator.log")
        full_log = stdout.read().decode('utf-8', errors='ignore')
        print(full_log)
        
        print()
        print("📋 Testing Python import directly...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 -c 'from backend.services.activity_points_system import activity_points_system; result = activity_points_system.get_leaderboard(10); print(result)' 2>&1")
        test1 = stdout.read().decode('utf-8', errors='ignore')
        print(test1)
        if stderr:
            err1 = stderr.read().decode('utf-8', errors='ignore')
            if err1:
                print("STDERR:", err1)
        
        stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 -c 'from backend.services.battle_intelligence_system import battle_intelligence_system; result = battle_intelligence_system.get_mode_intelligence(\"quick\", \"test_user\"); print(result)' 2>&1")
        test2 = stdout.read().decode('utf-8', errors='ignore')
        print(test2)
        if stderr:
            err2 = stderr.read().decode('utf-8', errors='ignore')
            if err2:
                print("STDERR:", err2)
        
        ssh.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    get_detailed_error()


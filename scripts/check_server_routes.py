#!/usr/bin/env python3
"""
Check Server Routes - Verify route files exist on server
"""
import paramiko
import os
import sys

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

ROUTE_FILES = [
    "backend/routes/agent_controller_routes.py",
    "backend/routes/agent_automation_routes.py",
    "backend/register_blueprints.py",
    "wsgi.py"
]

def check_server():
    """Check if route files exist on server"""
    print("=" * 70)
    print("Checking Server Route Files")
    print("=" * 70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        for route_file in ROUTE_FILES:
            remote_path = f"/var/www/html/vidgenerator/{route_file}"
            print(f"Checking: {route_file}")
            
            # Check if file exists
            stdin, stdout, stderr = ssh.exec_command(f"test -f {remote_path} && echo 'EXISTS' || echo 'NOT FOUND'", timeout=5)
            exists = stdout.read().decode().strip()
            
            if exists == "EXISTS":
                print(f"  ✅ File exists")
                
                # Check file size
                stdin, stdout, stderr = ssh.exec_command(f"wc -l {remote_path}", timeout=5)
                lines = stdout.read().decode().strip().split()[0]
                print(f"  📄 Lines: {lines}")
                
                # Check if it contains our routes
                if "agent_controller" in route_file:
                    stdin, stdout, stderr = ssh.exec_command(f"grep -c 'agent-controller/status' {remote_path} || echo '0'", timeout=5)
                    count = stdout.read().decode().strip()
                    print(f"  🔍 Contains 'agent-controller/status': {count} times")
                
                if "agent_automation" in route_file:
                    stdin, stdout, stderr = ssh.exec_command(f"grep -c 'agent/skillset/stats' {remote_path} || echo '0'", timeout=5)
                    count = stdout.read().decode().strip()
                    print(f"  🔍 Contains 'agent/skillset/stats': {count} times")
            else:
                print(f"  ❌ File NOT FOUND")
            
            print()
        
        # Check uWSGI logs for errors
        print("Checking uWSGI logs for errors...")
        stdin, stdout, stderr = ssh.exec_command("tail -50 /var/log/uwsgi/vidgenerator.log 2>/dev/null | grep -i 'error\\|import\\|blueprint' | tail -10 || echo 'No errors found'", timeout=5)
        logs = stdout.read().decode().strip()
        if logs and logs != "No errors found":
            print("  ⚠️  Recent errors in uWSGI log:")
            print(f"  {logs}")
        else:
            print("  ✅ No recent errors found")
        
        print()
        
        # Check if blueprints are registered
        print("Checking blueprint registration in wsgi.py...")
        stdin, stdout, stderr = ssh.exec_command("grep -c 'agent_controller_bp\\|agent_automation_bp' /var/www/html/vidgenerator/wsgi.py || echo '0'", timeout=5)
        count = stdout.read().decode().strip()
        print(f"  Found blueprint references: {count}")
        
        ssh.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    check_server()

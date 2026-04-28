#!/usr/bin/env python3
"""
Check Blueprint Imports - Test if blueprints can be imported
"""
import paramiko
import os
import sys

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def check_imports():
    """Check if blueprints can be imported on server"""
    print("=" * 70)
    print("Checking Blueprint Imports on Server")
    print("=" * 70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Test importing agent_controller_routes
        print("Testing: backend.routes.agent_controller_routes")
        cmd = "cd /var/www/html/vidgenerator && python3 -c \"from backend.routes.agent_controller_routes import agent_controller_bp; print('SUCCESS')\" 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode().strip()
        errors = stderr.read().decode().strip()
        
        if "SUCCESS" in output:
            print("  ✅ Import successful")
        else:
            print(f"  ❌ Import failed")
            if output:
                print(f"  Output: {output}")
            if errors:
                print(f"  Errors: {errors}")
        print()
        
        # Test importing agent_automation_routes
        print("Testing: backend.routes.agent_automation_routes")
        cmd = "cd /var/www/html/vidgenerator && python3 -c \"from backend.routes.agent_automation_routes import agent_automation_bp; print('SUCCESS')\" 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode().strip()
        errors = stderr.read().decode().strip()
        
        if "SUCCESS" in output:
            print("  ✅ Import successful")
        else:
            print(f"  ❌ Import failed")
            if output:
                print(f"  Output: {output}")
            if errors:
                print(f"  Errors: {errors}")
        print()
        
        # Check uWSGI error logs
        print("Checking uWSGI error logs...")
        stdin, stdout, stderr = ssh.exec_command("tail -100 /var/log/uwsgi/vidgenerator.log 2>/dev/null | grep -i 'agent_controller\\|agent_automation\\|import\\|error' | tail -20 || echo 'No relevant errors'", timeout=5)
        logs = stdout.read().decode().strip()
        if logs and "No relevant errors" not in logs:
            print("  ⚠️  Recent errors:")
            for line in logs.split('\n'):
                if line.strip():
                    print(f"  {line}")
        else:
            print("  ✅ No import errors found")
        print()
        
        # Check if services are available
        print("Testing service imports...")
        cmd = "cd /var/www/html/vidgenerator && python3 -c \"from backend.services.agent_controller import agent_controller; print('SUCCESS')\" 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode().strip()
        errors = stderr.read().decode().strip()
        
        if "SUCCESS" in output:
            print("  ✅ agent_controller service import successful")
        else:
            print(f"  ❌ agent_controller service import failed")
            if output:
                print(f"  Output: {output}")
            if errors:
                print(f"  Errors: {errors}")
        print()
        
        ssh.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    check_imports()

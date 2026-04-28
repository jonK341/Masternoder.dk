#!/usr/bin/env python3
"""
Verify Blueprint Registration
Checks if production_debugger and system_aggregator blueprints are registered
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def verify_blueprints():
    """Verify blueprint registrations on server"""
    print("="*80)
    print("VERIFYING BLUEPRINT REGISTRATIONS")
    print("="*80)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        # Check register_blueprints.py for the new blueprints
        print("[1/3] Checking register_blueprints.py...")
        stdin, stdout, stderr = ssh.exec_command(
            "grep -n 'production_debugger_bp\\|system_aggregator_bp' /var/www/html/backend/register_blueprints.py",
            timeout=5
        )
        output = stdout.read().decode()
        if output:
            print("  Found registrations:")
            for line in output.strip().split('\n'):
                print(f"    {line}")
        else:
            print("  [WARN] Blueprints not found in register_blueprints.py")
        print()
        
        # Check if files exist
        print("[2/3] Checking if route files exist...")
        files_to_check = [
            "/var/www/html/backend/routes/production_debugger_routes.py",
            "/var/www/html/backend/routes/system_aggregator_routes.py",
        ]
        for file_path in files_to_check:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {file_path} && echo 'EXISTS' || echo 'MISSING'", timeout=5)
            status = stdout.read().decode().strip()
            filename = os.path.basename(file_path)
            if status == "EXISTS":
                print(f"  ✓ {filename} exists")
            else:
                print(f"  ✗ {filename} MISSING")
        print()
        
        # Check uWSGI logs for registration
        print("[3/3] Checking uWSGI logs for blueprint registration...")
        stdin, stdout, stderr = ssh.exec_command(
            "journalctl -u uwsgi-vidgenerator -n 100 --no-pager | grep -i 'production_debugger\\|system_aggregator' | tail -5",
            timeout=5
        )
        log_output = stdout.read().decode()
        if log_output:
            print("  Recent log entries:")
            for line in log_output.strip().split('\n'):
                if line.strip():
                    print(f"    {line}")
        else:
            print("  No recent log entries found")
        
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_blueprints()

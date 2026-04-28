#!/usr/bin/env python3
"""
Diagnose Routes Script
Checks Flask application logs and route registration
"""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def diagnose_routes():
    """Diagnose route registration issues"""
    print("="*70)
    print("DIAGNOSING ROUTE REGISTRATION")
    print("="*70)
    print()
    
    try:
        # Connect
        print("[1/3] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Check uwsgi logs for errors
        print("[2/3] Checking uwsgi logs for errors...")
        log_commands = [
            ("tail -100 /var/log/uwsgi/app/vidgenerator.log 2>/dev/null | grep -i 'error\\|exception\\|traceback\\|blueprint\\|register' | tail -20", "uwsgi app log"),
            ("tail -100 /var/log/uwsgi/vidgenerator.log 2>/dev/null | grep -i 'error\\|exception\\|traceback\\|blueprint\\|register' | tail -20", "uwsgi log"),
            ("journalctl -u uwsgi -n 50 --no-pager 2>/dev/null | grep -i 'error\\|exception\\|blueprint' | tail -20", "systemd uwsgi"),
        ]
        
        for cmd, name in log_commands:
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
                output = stdout.read().decode().strip()
                error = stderr.read().decode().strip()
                if output:
                    print(f"  [INFO] {name}:")
                    for line in output.split('\n')[:10]:
                        if line.strip():
                            print(f"    {line[:100]}")
                elif error and 'No such file' not in error:
                    print(f"  [WARN] {name}: {error}")
            except Exception as e:
                print(f"  [ERROR] {name}: {e}")
        print()
        
        # Check if Flask app is running and can list routes
        print("[3/3] Testing Flask route registration...")
        test_script = """
import sys
sys.path.insert(0, '/var/www/html')
try:
    from src.app import create_app
    app = create_app()
    with app.app_context():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(f"{rule.endpoint}: {rule.rule} [{', '.join(rule.methods)}]")
        print("\\n".join(sorted(routes)[:50]))
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
"""
        
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 -c \"{test_script}\"",
            timeout=30
        )
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if output:
            print("  [OK] Found routes:")
            for line in output.split('\n')[:30]:
                if 'api' in line.lower() or 'static' in line.lower():
                    print(f"    {line}")
        if error:
            print(f"  [ERROR] {error}")
        
        print()
        print("="*70)
        print("DIAGNOSIS COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = diagnose_routes()
    sys.exit(0 if success else 1)

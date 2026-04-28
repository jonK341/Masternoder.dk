#!/usr/bin/env python3
"""
Check Flask Startup Errors
Checks Flask logs for startup errors preventing route registration
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_flask_errors():
    """Check Flask startup errors"""
    print("="*70)
    print("CHECKING FLASK STARTUP ERRORS")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Check uwsgi logs
        log_files = [
            "/var/log/uwsgi/app/vidgenerator.log",
            "/var/log/uwsgi/vidgenerator.log",
            "/var/log/uwsgi/vidgenerator-error.log",
        ]
        
        print("Checking Flask/uwsgi logs for errors...")
        for log_file in log_files:
            try:
                stdin, stdout, stderr = ssh.exec_command(f"tail -50 {log_file} 2>&1 | grep -i 'error\\|exception\\|traceback\\|failed' | tail -20", timeout=10)
                output = stdout.read().decode().strip()
                if output and 'No such file' not in output:
                    print(f"\n[LOG] {log_file}:")
                    for line in output.split('\n'):
                        if line.strip():
                            print(f"  {line[:150]}")
            except Exception as e:
                pass
        
        print()
        
        # Try to import routes directly
        print("Testing route imports on server...")
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html")
try:
    print("Testing imports...")
    from backend.routes.unified_dashboard_routes import unified_dashboard_bp
    print("OK: unified_dashboard_bp")
    from backend.routes.monetization_top50_routes import monetization_top50_bp
    print("OK: monetization_top50_bp")
    from backend.routes.agent_routes import agent_bp
    print("OK: agent_bp")
    from backend.routes.unified_points import unified_points_bp
    print("OK: unified_points_bp")
    from backend.routes.point_analytics_routes import point_analytics_bp
    print("OK: point_analytics_bp")
    from backend.routes.point_calculator_routes import point_calculator_bp
    print("OK: point_calculator_bp")
    from backend.routes.tech_tree_routes import tech_tree_bp
    print("OK: tech_tree_bp")
    print("SUCCESS: All blueprints imported")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
'''
        
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=30
        )
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        if output:
            print(output)
        if error:
            print(f"\n[ERROR] {error}")
        
        print()
        print("="*70)
        print("FLASK ERROR CHECK COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_flask_errors()

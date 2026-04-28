#!/usr/bin/env python3
"""
Check Blueprint Import Errors
Tests if production_debugger and system_aggregator blueprints can be imported
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_imports():
    """Check if blueprints can be imported"""
    print("="*80)
    print("CHECKING BLUEPRINT IMPORT ERRORS")
    print("="*80)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        # Test imports
        test_script = """
import sys
sys.path.insert(0, '/var/www/html')

try:
    from backend.routes.production_debugger_routes import production_debugger_bp
    print("SUCCESS: production_debugger_bp imported")
    print(f"Blueprint name: {production_debugger_bp.name}")
except Exception as e:
    print(f"ERROR importing production_debugger_bp: {e}")
    import traceback
    traceback.print_exc()

try:
    from backend.routes.system_aggregator_routes import system_aggregator_bp
    print("SUCCESS: system_aggregator_bp imported")
    print(f"Blueprint name: {system_aggregator_bp.name}")
except Exception as e:
    print(f"ERROR importing system_aggregator_bp: {e}")
    import traceback
    traceback.print_exc()

try:
    from backend.services.production_debugger import production_debugger
    print("SUCCESS: production_debugger imported")
except Exception as e:
    print(f"ERROR importing production_debugger: {e}")

try:
    from backend.services.system_aggregator import system_aggregator
    print("SUCCESS: system_aggregator imported")
except Exception as e:
    print(f"ERROR importing system_aggregator: {e}")
"""
        
        print("[1/2] Testing imports on server...")
        stdin, stdout, stderr = ssh.exec_command(
            f"cd /var/www/html && python3 -c {repr(test_script)}",
            timeout=10
        )
        output = stdout.read().decode()
        errors = stderr.read().decode()
        
        print(output)
        if errors:
            print("Errors:")
            print(errors)
        print()
        
        # Check registered routes
        print("[2/2] Checking registered routes...")
        route_check_script = """
import sys
sys.path.insert(0, '/var/www/html')
from src.app import create_app

app = create_app()
with app.app_context():
    routes = [str(rule) for rule in app.url_map.iter_rules() if 'debug' in str(rule) or 'aggregator' in str(rule)]
    print(f"Found {len(routes)} debug/aggregator routes:")
    for route in routes[:20]:
        print(f"  {route}")
"""
        
        stdin, stdout, stderr = ssh.exec_command(
            f"cd /var/www/html && python3 -c {repr(route_check_script)} 2>&1 | head -30",
            timeout=15
        )
        route_output = stdout.read().decode()
        route_errors = stderr.read().decode()
        
        print(route_output)
        if route_errors and 'Traceback' in route_errors:
            print("Errors:")
            print(route_errors[:500])
        
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_imports()

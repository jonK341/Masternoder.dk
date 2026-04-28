#!/usr/bin/env python3
"""
Simple Blueprint Import Test
Tests imports via SSH with a simple Python script file
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def test_imports():
    """Test blueprint imports"""
    print("="*80)
    print("TESTING BLUEPRINT IMPORTS")
    print("="*80)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        # Create test script on server
        test_script = """#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/www/html')

print("Testing imports...")
print()

try:
    from backend.routes.production_debugger_routes import production_debugger_bp
    print("SUCCESS: production_debugger_bp imported")
    print(f"  Blueprint name: {production_debugger_bp.name}")
    print(f"  Routes: {len(production_debugger_bp.deferred_functions)}")
except Exception as e:
    print(f"ERROR importing production_debugger_bp: {e}")
    import traceback
    traceback.print_exc()

print()

try:
    from backend.routes.system_aggregator_routes import system_aggregator_bp
    print("SUCCESS: system_aggregator_bp imported")
    print(f"  Blueprint name: {system_aggregator_bp.name}")
    print(f"  Routes: {len(system_aggregator_bp.deferred_functions)}")
except Exception as e:
    print(f"ERROR importing system_aggregator_bp: {e}")
    import traceback
    traceback.print_exc()

print()

try:
    from backend.services.production_debugger import production_debugger
    print("SUCCESS: production_debugger imported")
except Exception as e:
    print(f"ERROR importing production_debugger: {e}")

print()

try:
    from backend.services.system_aggregator import system_aggregator
    print("SUCCESS: system_aggregator imported")
except Exception as e:
    print(f"ERROR importing system_aggregator: {e}")
"""
        
        # Write script to server
        sftp = ssh.open_sftp()
        with sftp.file('/tmp/test_imports.py', 'w') as f:
            f.write(test_script)
        sftp.close()
        
        # Run script
        print("[1/1] Running import test...")
        stdin, stdout, stderr = ssh.exec_command(
            "cd /var/www/html && python3 /tmp/test_imports.py",
            timeout=15
        )
        output = stdout.read().decode()
        errors = stderr.read().decode()
        
        print(output)
        if errors and 'Traceback' in errors:
            print("\nErrors:")
            print(errors)
        
        # Cleanup
        ssh.exec_command("rm -f /tmp/test_imports.py", timeout=5)
        
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_imports()

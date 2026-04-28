#!/usr/bin/env python3
"""
Check App File Location
Checks where src/app.py is located
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_location():
    """Check app file location"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        app_paths = [
            "/var/www/html/vidgenerator/src/app.py",
            "/var/www/html/src/app.py",
            "/var/www/html/vidgenerator/app.py"
        ]
        
        print("Checking for app.py files...")
        print()
        
        for app_path in app_paths:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {app_path} && echo 'EXISTS' || echo 'NOT FOUND'", timeout=5)
            exists = stdout.read().decode().strip()
            print(f"{app_path}: {exists}")
            
            if exists == 'EXISTS':
                # Check if it has create_app function
                stdin2, stdout2, stderr2 = ssh.exec_command(f"grep -n 'def create_app' {app_path} | head -1", timeout=5)
                has_create = stdout2.read().decode().strip()
                if has_create:
                    print(f"  ✅ Has create_app function: {has_create}")
        
        # Also check the actual import path
        print()
        print("="*70)
        print("Testing import from wsgi.py location...")
        print("="*70)
        
        test_script = '''
import sys
import os

# Simulate what wsgi.py does
project_root = "/var/www/html/vidgenerator"
sys.path.insert(0, project_root)
os.chdir(project_root)

print(f"Python path: {sys.path[:3]}")
print(f"Current directory: {os.getcwd()}")

try:
    from src.app import create_app
    print("✅ Successfully imported from src.app")
    app = create_app()
    print("✅ Successfully created app")
    
    # Check if routes are registered
    routes_with_monetization = [str(r) for r in app.url_map.iter_rules() if 'monetization' in str(r)]
    if routes_with_monetization:
        print(f"✅ Found {len(routes_with_monetization)} routes with 'monetization':")
        for r in routes_with_monetization[:3]:
            print(f"  {r}")
    else:
        print("❌ No routes with 'monetization' found")
except ImportError as e:
    print(f"❌ Import error: {e}")
    # Try alternative paths
    sys.path.insert(0, "/var/www/html")
    try:
        from src.app import create_app
        print("✅ Successfully imported from /var/www/html/src/app")
    except ImportError as e2:
        print(f"❌ Also failed: {e2}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
'''
        
        stdin3, stdout3, stderr3 = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=60
        )
        output = stdout3.read().decode().strip()
        error = stderr3.read().decode().strip()
        if output:
            print(output)
        if error and "Traceback" in error:
            print(f"\n[ERROR OUTPUT]\n{error[:500]}")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_location()

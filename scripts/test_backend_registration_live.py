#!/usr/bin/env python3
"""
Test backend blueprint registration on live server
"""

import paramiko

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def test_live():
    """Test live server"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        
        print("=" * 70)
        print("Testing Backend Blueprint Registration on Live Server")
        print("=" * 70)
        print()
        
        # Test script
        test_script = """#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/www/html/vidgenerator')

from flask import Flask
from src.app import create_app

app = create_app()

print(f"Total blueprints: {len(app.blueprints)}")
print()

# Check backend blueprints
backend_bps = ['generator', 'gallery', 'game']
for bp_name in backend_bps:
    status = "[OK]" if bp_name in app.blueprints else "[MISSING]"
    print(f"{status} {bp_name}")

print()
print("Checking routes...")
target_routes = ['/api/gallery/list', '/api/generator/create', '/api/game/xp']
for target in target_routes:
    found = []
    for rule in app.url_map.iter_rules():
        if target in rule.rule:
            found.append(rule.rule)
    if found:
        print(f"[OK] {target}: {found[0]}")
    else:
        print(f"[MISSING] {target}")
"""
        
        # Write and run
        stdin, stdout, stderr = ssh_client.exec_command("cat > /tmp/test_live.py << 'PYTHON_SCRIPT'\n" + test_script + "\nPYTHON_SCRIPT")
        stdout.channel.recv_exit_status()
        
        cmd = "cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 /tmp/test_live.py 2>&1"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        
        print(output)
        if error and "Traceback" in error:
            print("\nErrors:")
            print(error[-1000:])
        
        ssh_client.exec_command("rm -f /tmp/test_live.py")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    test_live()

import os

#!/usr/bin/env python3
"""
Comprehensive server-side diagnostic test
Finds root cause of API route 404 issue
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def comprehensive_test():
    """Comprehensive server test"""
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
        print("COMPREHENSIVE SERVER DIAGNOSTIC TEST")
        print("=" * 70)
        print()
        
        # Create comprehensive test script
        test_script = """#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/var/www/html/vidgenerator')

print("=" * 70)
print("STEP 1: Test backend blueprint registration in isolation")
print("=" * 70)
print()

from flask import Flask
test_app = Flask(__name__)

# Register backend blueprints
from backend.register_blueprints import register_all_blueprints
register_all_blueprints(test_app)

print(f"\\nTest app blueprints: {list(test_app.blueprints.keys())}")
backend_bps = ['generator', 'gallery', 'game']
for bp_name in backend_bps:
    status = "[OK]" if bp_name in test_app.blueprints else "[MISSING]"
    print(f"  {status} {bp_name}")

print("\\n" + "=" * 70)
print("STEP 2: Test actual app creation step by step")
print("=" * 70)
print()

# Simulate app creation step by step
from src.app import create_app

# Capture all output
import io
from contextlib import redirect_stdout

f = io.StringIO()
with redirect_stdout(f):
    app = create_app()
output = f.getvalue()

# Check for backend registration messages
backend_msgs = [line for line in output.split('\\n') if '[Backend]' in line or 'register_all_blueprints' in line or 'Registered.*blueprint' in line]
if backend_msgs:
    print("Backend registration messages found:")
    for msg in backend_msgs[:10]:  # First 10
        print(f"  {msg}")
else:
    print("[ERROR] NO backend registration messages found!")

print(f"\\nActual app blueprints: {len(app.blueprints)} total")
backend_bps = ['generator', 'gallery', 'game']
for bp_name in backend_bps:
    status = "[OK]" if bp_name in app.blueprints else "[MISSING]"
    print(f"  {status} {bp_name}")

print("\\n" + "=" * 70)
print("STEP 3: Check blueprint registration order")
print("=" * 70)
print()

# Check if blueprints exist before register_routes
print("Checking blueprint registration timing...")

# Create app up to register_routes
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
import os

app2 = Flask(__name__)
app2.config['SECRET_KEY'] = 'test'
app2.wsgi_app = ProxyFix(app2.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

# Register backend FIRST
from backend.register_blueprints import register_all_blueprints
register_all_blueprints(app2)

print(f"After backend registration: {len(app2.blueprints)} blueprints")
for bp_name in backend_bps:
    status = "[OK]" if bp_name in app2.blueprints else "[MISSING]"
    print(f"  {status} {bp_name}")

# Now register routes
from src.web.routes import register_routes
register_routes(app2)

print(f"\\nAfter register_routes: {len(app2.blueprints)} blueprints")
for bp_name in backend_bps:
    status = "[OK]" if bp_name in app2.blueprints else "[MISSING]"
    print(f"  {status} {bp_name}")

print("\\n" + "=" * 70)
print("STEP 4: Check for blueprint name conflicts")
print("=" * 70)
print()

# Check all blueprint names
all_bp_names = list(app.blueprints.keys())
conflicts = [name for name in all_bp_names if name in ['generator', 'gallery', 'game']]
if conflicts:
    print(f"Found blueprint name conflicts: {conflicts}")
    for name in conflicts:
        bp = app.blueprints[name]
        print(f"  {name}: {type(bp).__name__} from {getattr(bp, '__module__', 'unknown')}")
else:
    print("No blueprint name conflicts found")

print("\\n" + "=" * 70)
print("STEP 5: Check routes")
print("=" * 70)
print()

target_routes = ['/api/gallery/list', '/api/generator/create', '/api/game/xp']
for target in target_routes:
    found = []
    for rule in app.url_map.iter_rules():
        if target in rule.rule:
            found.append(f"{rule.rule} {list(rule.methods)}")
    if found:
        print(f"[OK] {target}:")
        for route in found:
            print(f"    {route}")
    else:
        print(f"[MISSING] {target}")

print("\\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
"""
        
        # Write and run test script
        print("Creating comprehensive test script...")
        stdin, stdout, stderr = ssh_client.exec_command("cat > /tmp/test_comprehensive.py << 'PYTHON_SCRIPT'\n" + test_script + "\nPYTHON_SCRIPT")
        stdout.channel.recv_exit_status()
        
        print("Running comprehensive test...")
        print()
        cmd = "cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 /tmp/test_comprehensive.py 2>&1"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        
        print(output)
        if error and "Traceback" in error:
            print("\nErrors:")
            print(error[-3000:])
        
        # Clean up
        ssh_client.exec_command("rm -f /tmp/test_comprehensive.py")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    comprehensive_test()



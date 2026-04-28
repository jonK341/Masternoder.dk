#!/usr/bin/env python3
"""
Check if api_debugger routes are registered
"""

import paramiko

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def check_routes():
    """Check registered routes"""
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
        print("Checking API Debugger Routes")
        print("=" * 70)
        print()
        
        # Check if blueprint is registered
        cmd = """cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/var/www/html/vidgenerator')

from flask import Flask
from src.app import create_app

app = create_app()

# Check for api_debugger routes
api_debugger_routes = []
for rule in app.url_map.iter_rules():
    if 'api_debugger' in rule.endpoint or '/api/debugger' in rule.rule:
        api_debugger_routes.append({
            'endpoint': rule.endpoint,
            'rule': rule.rule,
            'methods': list(rule.methods)
        })

print(f"Found {len(api_debugger_routes)} api_debugger routes:")
for route in api_debugger_routes[:10]:
    print(f"  {route['rule']} [{', '.join(route['methods'])}]")

# Check blueprints
print(f"\\nTotal blueprints: {len(app.blueprints)}")
if 'api_debugger' in app.blueprints:
    print("✅ api_debugger blueprint is registered")
else:
    print("❌ api_debugger blueprint NOT registered")
    print(f"Available blueprints: {list(app.blueprints.keys())[:20]}")
PYTHON_SCRIPT"""
        
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        
        print(output)
        if error and "Traceback" in error:
            print("\nErrors:")
            print(error[-1000:])
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    check_routes()

import os

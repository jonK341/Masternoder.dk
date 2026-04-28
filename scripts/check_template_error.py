#!/usr/bin/env python3
"""
Check for template rendering errors
"""

import paramiko

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def check_error():
    """Check for errors"""
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
        print("Checking Template Rendering")
        print("=" * 70)
        print()
        
        # Test template rendering directly
        cmd = """cd /var/www/html/vidgenerator && source .venv/bin/activate && python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/var/www/html/vidgenerator')

from flask import Flask
from flask import render_template

app = Flask(__name__)
app.config['TEMPLATE_FOLDER'] = '/var/www/html/vidgenerator/vidgenerator/templates'

# Test rendering
try:
    with app.app_context():
        result = render_template('api_debugger.html')
        print("✅ Template rendered successfully!")
        print(f"   Length: {len(result)} characters")
        if "Rettigheder" in result:
            print("   ✅ Contains 'Rettigheder'")
        else:
            print("   ❌ Does NOT contain 'Rettigheder'")
except Exception as e:
    print(f"❌ Template rendering failed: {e}")
    import traceback
    traceback.print_exc()
PYTHON_SCRIPT"""
        
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        
        print(output)
        if error and "Traceback" in error:
            print("\nErrors:")
            print(error)
        
        # Check uWSGI logs
        print("\n" + "=" * 70)
        print("Checking uWSGI Logs (last 20 lines)")
        print("=" * 70)
        print()
        
        cmd2 = "journalctl -u uwsgi-vidgenerator.service -n 20 --no-pager 2>/dev/null | grep -i 'api_debugger\|template\|error' | tail -10"
        stdin2, stdout2, stderr2 = ssh_client.exec_command(cmd2)
        logs = stdout2.read().decode()
        if logs:
            print(logs)
        else:
            print("No relevant log entries found")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    check_error()

import os

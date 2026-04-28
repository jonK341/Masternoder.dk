#!/usr/bin/env python3
"""
Test Middleware Stripping
Tests if middleware is correctly stripping /vidgenerator
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def test_middleware():
    """Test middleware"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Check uwsgi logs for middleware output
        print("Checking uwsgi logs for middleware PATH_INFO...")
        print()
        
        # Make a test request first
        cmd1 = "curl -s https://masternoder.dk/vidgenerator/api/monetization/top50?limit=6 > /dev/null 2>&1"
        stdin1, stdout1, stderr1 = ssh.exec_command(cmd1, timeout=5)
        stdout1.read()
        
        # Check logs
        cmd2 = "tail -20 /var/www/html/vidgenerator/uwsgi.log | grep -A 2 'monetization/top50' | head -10"
        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=5)
        output = stdout2.read().decode().strip()
        print(output)
        
        # Also check what Flask sees
        print()
        print("="*70)
        print("Checking what Flask sees for the route...")
        print("="*70)
        
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html")

from src.app import create_app
from flask import Flask

app = create_app()

# Check if route exists
with app.test_request_context('/api/monetization/top50'):
    from flask import request
    print(f"PATH_INFO: {request.environ.get('PATH_INFO')}")
    print(f"Request path: {request.path}")
    
    # Try to match the route
    adapter = app.url_map.bind('masternoder.dk')
    try:
        endpoint, values = adapter.match('/api/monetization/top50')
        print(f"✅ Route matched! Endpoint: {endpoint}")
    except Exception as e:
        print(f"❌ Route NOT matched: {e}")
        # Show available routes
        print("\\nAvailable routes with 'monetization':")
        for rule in app.url_map.iter_rules():
            if 'monetization' in str(rule):
                print(f"  {rule}")
'''
        
        stdin3, stdout3, stderr3 = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=60
        )
        output3 = stdout3.read().decode().strip()
        error3 = stderr3.read().decode().strip()
        if output3:
            print(output3)
        if error3 and "Traceback" in error3:
            print(f"\n[ERROR OUTPUT]\n{error3[:500]}")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_middleware()

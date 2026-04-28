#!/usr/bin/env python3
"""
Test Nginx Rewrite Direct
Tests if nginx rewrite is working correctly
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def test_rewrite():
    """Test nginx rewrite"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Test with /vidgenerator/api prefix (what frontend uses)
        route = "/vidgenerator/api/monetization/top50?limit=6"
        url = f"https://masternoder.dk{route}"
        
        print(f"Testing: {url}")
        print()
        print("This should be rewritten by nginx to: /api/monetization/top50")
        print("Then Flask middleware should see: /api/monetization/top50")
        print("Then Flask should match the route registered as: /api/monetization/top50")
        print()
        
        # Make request and check uwsgi logs
        cmd = f"curl -s {url} > /dev/null 2>&1 && sleep 1 && tail -5 /var/www/html/vidgenerator/uwsgi.log | grep -A 1 'monetization/top50'"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode().strip()
        print("uWSGI log output:")
        print(output)
        
        # Also test directly via uWSGI to see if route works
        print()
        print("="*70)
        print("Testing directly via uWSGI (bypassing nginx):")
        print("="*70)
        cmd2 = "curl -s http://127.0.0.1:5000/api/monetization/top50?limit=6 | head -5"
        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=10)
        output2 = stdout2.read().decode().strip()
        print(output2)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_rewrite()

#!/usr/bin/env python3
"""
Test Direct uWSGI
Tests route directly via uWSGI (bypassing nginx)
"""
import paramiko
import os
import json

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def test_direct():
    """Test directly via uWSGI"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Test directly via uWSGI on localhost:5000
        route = "/api/monetization/top50?limit=6"
        url = f"http://127.0.0.1:5000{route}"
        
        print(f"Testing directly via uWSGI: {url}")
        print()
        
        cmd = f"curl -s -w '\\nHTTP_STATUS:%{{http_code}}' {url} 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode().strip()
        
        # Extract status and body
        if 'HTTP_STATUS:' in output:
            parts = output.split('HTTP_STATUS:')
            body = parts[0].strip()
            status = parts[1].strip() if len(parts) > 1 else 'unknown'
        else:
            body = output
            status = 'unknown'
        
        print(f"Status: {status}")
        if body:
            try:
                data = json.loads(body)
                print("✅ Valid JSON:")
                print(json.dumps(data, indent=2)[:200])
            except:
                print(f"Response: {body[:200]}")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_direct()

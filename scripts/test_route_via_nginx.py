#!/usr/bin/env python3
"""
Test Route Via Nginx
Tests a route via nginx to see what's happening
"""
import paramiko
import os
import json

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def test_route():
    """Test route via nginx"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Test route with /vidgenerator/api prefix
        route = "/vidgenerator/api/monetization/top50?limit=6"
        url = f"https://masternoder.dk{route}"
        
        print(f"Testing: {url}")
        print()
        
        cmd = f"curl -s -w '\\nHTTP_STATUS:%{{http_code}}' {url} 2>&1 | head -10"
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
        print(f"Response: {body[:200]}")
        
        # Check if it's JSON
        if body:
            try:
                data = json.loads(body)
                print()
                print("✅ Valid JSON response:")
                print(json.dumps(data, indent=2)[:300])
            except:
                if '<!doctype' in body.lower() or '<html' in body.lower():
                    print()
                    print("❌ HTML response (404 page)")
                else:
                    print()
                    print("⚠️  Not JSON")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_route()

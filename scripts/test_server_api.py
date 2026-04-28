#!/usr/bin/env python3
"""
Test API endpoints directly on server
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def test_server_api():
    """Test API endpoints on server"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        
        print("=" * 60)
        print("Testing API endpoints on server")
        print("=" * 60)
        print()
        
        # Test endpoints
        endpoints = [
            ("GET", "/api/gallery/list"),
            ("POST", "/api/generator/create"),
            ("POST", "/api/game/xp"),
            ("GET", "/api/debug/errors/scan"),
        ]
        
        for method, endpoint in endpoints:
            print(f"Testing {method} {endpoint}...")
            
            if method == "POST":
                cmd = f"curl -s -X POST http://127.0.0.1:5000{endpoint} -H 'Content-Type: application/json' -d '{{}}' -w '\\nHTTP_CODE:%{{http_code}}'"
            else:
                cmd = f"curl -s http://127.0.0.1:5000{endpoint} -w '\\nHTTP_CODE:%{{http_code}}'"
            
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            output = stdout.read().decode()
            error = stderr.read().decode()
            
            if "HTTP_CODE:200" in output or "HTTP_CODE:500" in output:
                status = output.split("HTTP_CODE:")[-1].strip()
                print(f"  ✅ Status: {status}")
            elif "HTTP_CODE:404" in output:
                print(f"  ❌ Status: 404")
            else:
                print(f"  ⚠️  Response: {output[:100]}")
                if error:
                    print(f"  Error: {error[:100]}")
            print()
        
        # Check logs for blueprint registration
        print("Checking server logs for blueprint registration...")
        cmd = "journalctl -u python-proxy.service --no-pager -n 100 | grep -i 'backend\|blueprint\|gallery\|generator\|game' | tail -20"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        logs = stdout.read().decode()
        
        if logs:
            print(logs)
        else:
            print("  No relevant logs found")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    test_server_api()

import os

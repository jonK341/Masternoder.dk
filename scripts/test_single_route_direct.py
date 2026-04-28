#!/usr/bin/env python3
"""
Test Single Route Direct
Tests a single route directly on the server
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def test_route():
    """Test a single route"""
    print("="*70)
    print("TESTING SINGLE ROUTE DIRECTLY")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Test route via HTTPS (through nginx)
        test_url = "https://masternoder.dk/vidgenerator/api/unified-dashboard/data?user_id=test_user_1"
        print(f"Testing: {test_url}")
        print()
        
        cmd = f"curl -s -w '\nHTTP_STATUS:%{{http_code}}\n' {test_url} 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        print("Response:")
        print(output)
        if error:
            print(f"\nError output:\n{error}")
        
        print()
        print("="*70)
        print("TEST COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_route()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Error API Directly on Server
Tests the error logging API by making direct requests to the server
"""
import paramiko
import os
import json

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def test_error_api_direct():
    """Test error API directly on server"""
    print("=" * 70)
    print("TESTING ERROR API DIRECTLY ON SERVER")
    print("=" * 70)
    print()
    
    ssh = None
    try:
        print("Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Test 1: Check if routes are registered
        print("Test 1: Checking registered routes...")
        stdin, stdout, stderr = ssh.exec_command(
            "cd /var/www/html && python3 -c \"from src.app import create_app; app = create_app(); routes = [str(r) for r in app.url_map.iter_rules() if 'error' in str(r).lower()]; print('\\n'.join(sorted(routes)[:20]))\" 2>&1",
            timeout=30
        )
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        print("  Routes with 'error':")
        if output:
            for line in output.split('\n')[:10]:
                if line.strip():
                    print(f"    {line}")
        if error and 'Error' in error:
            print(f"  [WARN] {error[:200]}")
        print()
        
        # Test 2: Test API endpoint via curl
        print("Test 2: Testing /vidgenerator/api/errors/stats via curl...")
        stdin, stdout, stderr = ssh.exec_command(
            "curl -s http://localhost:8080/vidgenerator/api/errors/stats?days=1 2>&1 | head -50",
            timeout=10
        )
        output = stdout.read().decode('utf-8', errors='ignore')
        if 'success' in output.lower() or 'total_errors' in output.lower():
            print("  [OK] API endpoint is working!")
            print(f"  Response: {output[:300]}")
        elif '404' in output or 'Not Found' in output:
            print("  [ERROR] 404 - Route not found")
            print(f"  Response: {output[:200]}")
        else:
            print(f"  [INFO] Response: {output[:200]}")
        print()
        
        # Test 3: Check if blueprint is loaded
        print("Test 3: Checking if error_logging blueprint is registered...")
        stdin, stdout, stderr = ssh.exec_command(
            "cd /var/www/html && python3 -c \"from src.app import create_app; app = create_app(); print('error_logging' in app.blueprints); print(list(app.blueprints.keys())[-10:])\" 2>&1",
            timeout=30
        )
        output = stdout.read().decode('utf-8', errors='ignore')
        print(f"  Blueprint check: {output[:200]}")
        print()
        
        # Test 4: Check service status
        print("Test 4: Checking service status...")
        for service in ['python-proxy', 'nginx']:
            stdin, stdout, stderr = ssh.exec_command(
                f"systemctl is-active {service} 2>&1",
                timeout=5
            )
            status = stdout.read().decode('utf-8', errors='ignore').strip()
            print(f"  {service}: {status}")
        print()
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if ssh:
            ssh.close()

if __name__ == '__main__':
    test_error_api_direct()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify Services Status
Checks if all services are running properly after deployment
"""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def verify_services():
    """Verify all services are running"""
    print("=" * 70)
    print("VERIFYING SERVICES STATUS")
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
        
        services = [
            'python-proxy.service',
            'uwsgi-vidgenerator',
            'nginx',
            'apache2'
        ]
        
        print("Checking service statuses...")
        print()
        
        all_ok = True
        for service in services:
            try:
                # Check if service exists and get status
                stdin, stdout, stderr = ssh.exec_command(
                    f"systemctl is-active {service} 2>&1 || service {service} status 2>&1 | head -1 || echo 'not_found'",
                    timeout=10
                )
                status = stdout.read().decode('utf-8', errors='ignore').strip()
                error = stderr.read().decode('utf-8', errors='ignore').strip()
                
                if 'active' in status.lower() or 'running' in status.lower():
                    print(f"  [OK] {service}: {status}")
                elif 'not_found' in status or 'could not be found' in error.lower():
                    print(f"  [SKIP] {service}: Not found (may not be installed)")
                else:
                    print(f"  [WARN] {service}: {status}")
                    if error:
                        print(f"         Error: {error[:100]}")
                    all_ok = False
            except Exception as e:
                print(f"  [ERROR] {service}: {e}")
                all_ok = False
        
        print()
        
        # Check if error logging API is accessible
        print("Testing error logging API...")
        try:
            stdin, stdout, stderr = ssh.exec_command(
                "curl -s http://localhost:8080/vidgenerator/api/errors/stats?days=1 2>&1 | head -20",
                timeout=10
            )
            output = stdout.read().decode('utf-8', errors='ignore')
            if 'success' in output.lower() or 'total_errors' in output.lower():
                print("  [OK] Error logging API is responding")
            else:
                print(f"  [WARN] Error logging API response: {output[:200]}")
        except Exception as e:
            print(f"  [WARN] Could not test API: {e}")
        
        print()
        print("=" * 70)
        if all_ok:
            print("ALL SERVICES VERIFIED")
        else:
            print("SOME SERVICES NEED ATTENTION")
        print("=" * 70)
        
        return all_ok
        
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if ssh:
            ssh.close()

if __name__ == '__main__':
    success = verify_services()
    sys.exit(0 if success else 1)

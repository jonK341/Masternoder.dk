#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Frontpage - Check Services and Activity
Tests if all services are running and why page might not update
"""
import paramiko
import os
import sys
import requests
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_services():
    """Check if all Flask/uWSGI services are running"""
    print("="*70)
    print("DEBUGGING FRONTPAGE - Service Check")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect to server
        print("[1/6] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Check service status
        print("[2/6] Checking service status...")
        services = ['uwsgi', 'uwsgi-vidgenerator', 'python-proxy']
        service_status = {}
        
        for service in services:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service} 2>&1", timeout=5)
            status = stdout.read().decode().strip()
            service_status[service] = status
            
            if status == "active":
                print(f"  [OK] {service}: ACTIVE")
            else:
                print(f"  [FAIL] {service}: {status}")
                
                # Get more details
                stdin, stdout, stderr = ssh.exec_command(f"systemctl status {service} --no-pager -l | head -20", timeout=5)
                details = stdout.read().decode('utf-8', errors='replace').strip()
                if details:
                    print(f"    Details: {details[:200]}")
        
        print()
        
        # Check if processes are running
        print("[3/6] Checking running processes...")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep -E '(uwsgi|flask|python.*run)' | grep -v grep", timeout=5)
        processes = stdout.read().decode().strip()
        if processes:
            print("  [OK] Found processes:")
            for line in processes.split('\n'):
                if line.strip():
                    print(f"    {line[:100]}")
        else:
            print("  [WARN] No uwsgi/flask processes found")
        print()
        
        # Check recent logs
        print("[4/6] Checking recent uwsgi logs...")
        stdin, stdout, stderr = ssh.exec_command("journalctl -u uwsgi -n 30 --no-pager 2>&1", timeout=10)
        logs = stdout.read().decode().strip()
        if logs:
            print("  Recent logs:")
            for line in logs.split('\n')[-10:]:
                if line.strip():
                    print(f"    {line[:120]}")
        else:
            print("  [WARN] No logs found")
        print()
        
        # Test frontpage URL
        print("[5/6] Testing frontpage URL...")
        try:
            url = "https://masternoder.dk/vidgenerator/"
            response = requests.get(url, timeout=10, verify=False)
            print(f"  Status Code: {response.status_code}")
            print(f"  Content Length: {len(response.content)} bytes")
            print(f"  Content Type: {response.headers.get('Content-Type', 'Unknown')}")
            print(f"  Cache Control: {response.headers.get('Cache-Control', 'Not set')}")
            
            # Check if HTML contains engine code
            if '[Engine]' in response.text:
                print("  [OK] HTML contains engine code")
            else:
                print("  [WARN] HTML does not contain '[Engine]' code")
            
            # Check if scripts are referenced
            if 'unified-point-counters.js' in response.text:
                print("  [OK] unified-point-counters.js referenced")
            else:
                print("  [WARN] unified-point-counters.js not found in HTML")
                
        except Exception as e:
            print(f"  [ERROR] Failed to test URL: {e}")
        print()
        
        # Test API endpoints
        print("[6/6] Testing API endpoints...")
        api_endpoints = [
            "/vidgenerator/api/stats/summary",
            "/vidgenerator/api/points/all?user_id=test",
        ]
        
        for endpoint in api_endpoints:
            try:
                url = f"https://masternoder.dk{endpoint}"
                response = requests.get(url, timeout=5, verify=False)
                if response.status_code == 200:
                    print(f"  [OK] {endpoint}: {response.status_code}")
                    try:
                        data = response.json()
                        if data.get('success'):
                            print(f"    Success: {data.get('success')}")
                    except:
                        pass
                else:
                    print(f"  [FAIL] {endpoint}: {response.status_code}")
            except Exception as e:
                print(f"  [ERROR] {endpoint}: {e}")
        
        print()
        print("="*70)
        print("DEBUG SUMMARY")
        print("="*70)
        
        # Summary
        active_count = sum(1 for s in service_status.values() if s == "active")
        print(f"Services active: {active_count}/{len(services)}")
        
        if active_count == len(services):
            print("[OK] All services are running")
        else:
            print("[FAIL] Some services are not running")
            print("  Action: Restart services with 'python deploy.py'")
        
        print()
        print("Next steps:")
        print("1. Check browser console (F12) for JavaScript errors")
        print("2. Look for '[Engine]' logs in console")
        print("3. Check if counters are updating")
        print("4. Verify scripts are loading (Network tab)")
        print()
        
        ssh.close()
        return active_count == len(services)
        
    except Exception as e:
        print(f"[ERROR] Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Disable SSL warnings for testing
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    success = check_services()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Check Flask status on masternoder.dk server
Uses SSH to check if Flask is running on the production server
"""

import paramiko
import requests
import sys
from typing import Dict, Optional

# Server credentials
SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def check_live_site() -> Dict[str, any]:
    """Check if the live site is accessible"""
    print("=" * 60)
    print("Method 1: Checking Live Site")
    print("=" * 60)
    print()
    
    results = {}
    
    # Check main page
    try:
        response = requests.get("https://masternoder.dk/vidgenerator", timeout=10)
        results['main_page'] = {
            'accessible': True,
            'status_code': response.status_code,
            'size': len(response.content),
            'content_type': response.headers.get('Content-Type', '')
        }
        print(f"[OK] Main page accessible: {response.status_code} ({len(response.content)} bytes)")
    except Exception as e:
        results['main_page'] = {
            'accessible': False,
            'error': str(e)
        }
        print(f"[ERROR] Main page not accessible: {e}")
    
    # Check health endpoint
    try:
        response = requests.get("https://masternoder.dk/health", timeout=10)
        results['health'] = {
            'accessible': True,
            'status_code': response.status_code,
            'response': response.json() if response.headers.get('Content-Type', '').startswith('application/json') else response.text
        }
        print(f"[OK] Health endpoint accessible: {response.status_code}")
        print(f"      Response: {results['health']['response']}")
    except Exception as e:
        results['health'] = {
            'accessible': False,
            'error': str(e)
        }
        print(f"[WARN] Health endpoint not accessible: {e}")
    
    print()
    return results

def check_ssh_flask_process() -> Dict[str, any]:
    """Check Flask process via SSH"""
    print("=" * 60)
    print("Method 2: Checking Flask Process via SSH")
    print("=" * 60)
    print()
    
    results = {}
    
    try:
        print(f"Connecting to {SERVER_HOST}...")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=10,
            look_for_keys=False,
            allow_agent=False
        )
        print("[OK] SSH connection successful!")
        print()
        
        # Check Flask processes
        print("Checking for Flask processes...")
        stdin, stdout, stderr = ssh_client.exec_command("ps aux | grep -i flask | grep -v grep")
        flask_processes = stdout.read().decode().strip()
        
        if flask_processes:
            print("[OK] Flask processes found:")
            print()
            for line in flask_processes.split('\n'):
                if line.strip():
                    print(f"  {line}")
            results['flask_processes'] = flask_processes.split('\n')
            results['flask_running'] = True
        else:
            print("[WARN] No Flask processes found")
            results['flask_running'] = False
        
        print()
        
        # Check port 5000
        print("Checking port 5000...")
        stdin, stdout, stderr = ssh_client.exec_command("netstat -tuln | grep :5000 || ss -tuln | grep :5000")
        port_info = stdout.read().decode().strip()
        
        if port_info:
            print("[OK] Port 5000 is in use:")
            print(f"  {port_info}")
            results['port_5000'] = port_info
        else:
            print("[INFO] Port 5000 is not in use (may be using different port or nginx)")
            results['port_5000'] = None
        
        print()
        
        # Check systemd service (if exists)
        print("Checking systemd services...")
        stdin, stdout, stderr = ssh_client.exec_command("systemctl list-units --type=service | grep -i flask || echo 'No Flask systemd service found'")
        systemd_info = stdout.read().decode().strip()
        
        if 'flask' in systemd_info.lower() and 'No Flask' not in systemd_info:
            print("[OK] Flask systemd service found:")
            print(f"  {systemd_info}")
            results['systemd_service'] = systemd_info
        else:
            print("[INFO] No Flask systemd service found")
            results['systemd_service'] = None
        
        print()
        
        # Check nginx status
        print("Checking nginx status...")
        stdin, stdout, stderr = ssh_client.exec_command("systemctl status nginx --no-pager | head -5 || echo 'Nginx check failed'")
        nginx_info = stdout.read().decode().strip()
        
        if 'active' in nginx_info.lower():
            print("[OK] Nginx is running")
            print(f"  {nginx_info.split(chr(10))[0]}")
            results['nginx_running'] = True
        else:
            print("[WARN] Nginx status unclear")
            results['nginx_running'] = None
        
        ssh_client.close()
        
    except paramiko.AuthenticationException:
        print("[ERROR] SSH authentication failed!")
        results['error'] = 'Authentication failed'
    except paramiko.SSHException as e:
        print(f"[ERROR] SSH error: {e}")
        results['error'] = str(e)
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        results['error'] = str(e)
    
    print()
    return results

def main():
    """Main function"""
    print()
    print("=" * 60)
    print("Flask Server Status Check - masternoder.dk")
    print("=" * 60)
    print()
    
    # Check live site
    site_results = check_live_site()
    
    # Check SSH
    ssh_results = check_ssh_flask_process()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()
    
    if site_results.get('main_page', {}).get('accessible'):
        print("[OK] Live site is accessible")
    else:
        print("[ERROR] Live site is not accessible")
    
    if ssh_results.get('flask_running'):
        print("[OK] Flask process is running on server")
    elif ssh_results.get('flask_running') == False:
        print("[WARN] Flask process not found (may be running under different name)")
    else:
        print("[WARN] Could not verify Flask process status")
    
    if ssh_results.get('nginx_running'):
        print("[OK] Nginx is running")
    
    print()
    
    # Exit code
    if site_results.get('main_page', {}).get('accessible'):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()

import os

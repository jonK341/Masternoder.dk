#!/usr/bin/env python3
"""
Verify and Fix Server Files - Check what's on server and update cache versions
"""
import paramiko
import os
import sys
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html/vidgenerator"

def verify_and_fix():
    """Verify server files and update cache versions"""
    print("=" * 70)
    print("VERIFY AND FIX SERVER FILES")
    print("=" * 70)
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect
        print("[1/4] Connecting to server...")
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Check backend-connector.js
        print("[2/4] Checking backend-connector.js on server...")
        sftp = ssh.open_sftp()
        try:
            remote_file = sftp.open(f'{SERVER_BASE}/static/js/backend-connector.js', 'r')
            remote_content = remote_file.read().decode('utf-8')
            remote_file.close()
            
            has_fix = '/user/profile/' in remote_content and 'async getStats' in remote_content
            print(f"  Size: {len(remote_content)} bytes")
            print(f"  Has getStats fix: {has_fix}")
            
            # Show getStats method
            if 'async getStats' in remote_content:
                start = remote_content.find('async getStats')
                end = start + 300
                print(f"  getStats method (first 300 chars):")
                print(f"    {remote_content[start:end]}")
        except Exception as e:
            print(f"  [ERROR] {e}")
        
        print()
        
        # Check profile/index.html and update cache version
        print("[3/4] Checking and updating profile/index.html...")
        try:
            remote_file = sftp.open(f'{SERVER_BASE}/profile/index.html', 'r')
            remote_content = remote_file.read().decode('utf-8')
            remote_file.close()
            
            has_fix = 'initProfileManager' in remote_content
            print(f"  Size: {len(remote_content)} bytes")
            print(f"  Has init fix: {has_fix}")
            
            # Update cache version for backend-connector.js
            new_version = datetime.now().strftime("%Y%m%d%H%M%S")
            old_pattern = r'(src=["\']/vidgenerator/static/js/backend-connector\.js\?v=)([\d]+)'
            new_replacement = r'\1' + new_version
            
            if re.search(old_pattern, remote_content):
                updated_content = re.sub(old_pattern, new_replacement, remote_content)
                
                # Write back
                remote_file = sftp.open(f'{SERVER_BASE}/profile/index.html', 'w')
                remote_file.write(updated_content.encode('utf-8'))
                remote_file.close()
                
                print(f"  [OK] Updated cache version to: {new_version}")
            else:
                print(f"  [WARN] Cache version pattern not found, adding it...")
                # Add version if missing
                pattern = r'(src=["\']/vidgenerator/static/js/backend-connector\.js)(")'
                replacement = r'\1?v=' + new_version + r'\2'
                updated_content = re.sub(pattern, replacement, remote_content)
                
                remote_file = sftp.open(f'{SERVER_BASE}/profile/index.html', 'w')
                remote_file.write(updated_content.encode('utf-8'))
                remote_file.close()
                
                print(f"  [OK] Added cache version: {new_version}")
                
        except Exception as e:
            print(f"  [ERROR] {e}")
        
        sftp.close()
        print()
        
        # Restart services
        print("[4/4] Restarting services...")
        import time
        
        # Stop
        ssh.exec_command("systemctl stop uwsgi-vidgenerator > /dev/null 2>&1 &", timeout=5)
        time.sleep(3)
        ssh.exec_command("systemctl stop python-proxy > /dev/null 2>&1 &", timeout=5)
        time.sleep(3)
        
        # Start
        ssh.exec_command("systemctl start uwsgi-vidgenerator > /dev/null 2>&1 &", timeout=5)
        time.sleep(5)
        ssh.exec_command("systemctl start python-proxy > /dev/null 2>&1 &", timeout=5)
        time.sleep(5)
        
        print("  [OK] Services restarted")
        print()
        
        print("=" * 70)
        print("VERIFICATION COMPLETE")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Clear browser cache completely (Ctrl+Shift+Delete)")
        print("  2. Or use incognito/private window")
        print("  3. Visit: https://masternoder.dk/vidgenerator/profile")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    verify_and_fix()

#!/usr/bin/env python3
"""
Verify Server Files Match Local
"""
import paramiko
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html/vidgenerator"

def verify_files():
    """Verify server files match local"""
    print("=" * 70)
    print("VERIFYING SERVER FILES")
    print("=" * 70)
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        
        # Check profile/index.html
        print("[1/2] Checking profile/index.html...")
        local_file = os.path.join(BASE_DIR, 'vidgenerator/profile/index.html')
        remote_file = f'{SERVER_BASE}/profile/index.html'
        
        with open(local_file, 'r', encoding='utf-8') as f:
            local_content = f.read()
        
        remote_file_obj = sftp.open(remote_file, 'r')
        remote_content = remote_file_obj.read().decode('utf-8')
        remote_file_obj.close()
        
        # Check key indicators
        local_has = {
            'loadPointsStats': 'loadPointsStats' in local_content,
            'initProfileManager': 'initProfileManager' in local_content,
            'loadDetailedStats': 'loadDetailedStats' in local_content,
            'backend-connector.js': 'backend-connector.js' in local_content,
        }
        
        remote_has = {
            'loadPointsStats': 'loadPointsStats' in remote_content,
            'initProfileManager': 'initProfileManager' in remote_content,
            'loadDetailedStats': 'loadDetailedStats' in remote_content,
            'backend-connector.js': 'backend-connector.js' in remote_content,
        }
        
        print("\n  Local file indicators:")
        for key, value in local_has.items():
            print(f"    {'[OK]' if value else '[MISS]'} {key}: {value}")
        
        print("\n  Remote file indicators:")
        for key, value in remote_has.items():
            print(f"    {'[OK]' if value else '[MISS]'} {key}: {value}")
        
        # Check cache version
        import re
        local_cache = re.search(r'backend-connector\.js\?v=(\d+)', local_content)
        remote_cache = re.search(r'backend-connector\.js\?v=(\d+)', remote_content)
        
        print(f"\n  Local cache version: {local_cache.group(1) if local_cache else 'NOT FOUND'}")
        print(f"  Remote cache version: {remote_cache.group(1) if remote_cache else 'NOT FOUND'}")
        
        # Check if files match
        if local_content == remote_content:
            print("\n  [OK] Files match exactly")
        else:
            print("\n  [WARN] Files differ")
            print(f"  Local size: {len(local_content)} bytes")
            print(f"  Remote size: {len(remote_content)} bytes")
        
        sftp.close()
        ssh.close()
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    verify_files()

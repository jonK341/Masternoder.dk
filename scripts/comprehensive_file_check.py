#!/usr/bin/env python3
"""
Comprehensive File Check - Compare local vs server files in detail
"""
import paramiko
import os
import sys
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html/vidgenerator"

FILES_TO_CHECK = [
    {
        'local': 'vidgenerator/static/js/backend-connector.js',
        'remote': f'{SERVER_BASE}/static/js/backend-connector.js',
        'key_indicators': ['async getStats', '/user/profile/', 'fallback']
    },
    {
        'local': 'vidgenerator/profile/index.html',
        'remote': f'{SERVER_BASE}/profile/index.html',
        'key_indicators': ['initProfileManager', 'backendConnector', 'typeof']
    },
]

def check_files_comprehensive():
    """Comprehensive check of local vs server files"""
    print("=" * 70)
    print("COMPREHENSIVE FILE CHECK")
    print("=" * 70)
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        
        for item in FILES_TO_CHECK:
            local_path = os.path.join(BASE_DIR, item['local'])
            remote_path = item['remote']
            
            print(f"File: {os.path.basename(item['local'])}")
            print("-" * 70)
            
            # Read local
            if os.path.exists(local_path):
                with open(local_path, 'r', encoding='utf-8') as f:
                    local_content = f.read()
                local_size = len(local_content)
            else:
                print("  [ERROR] Local file not found")
                continue
            
            # Read remote
            try:
                remote_file = sftp.open(remote_path, 'r')
                remote_content = remote_file.read().decode('utf-8')
                remote_file.close()
                remote_size = len(remote_content)
            except Exception as e:
                print(f"  [ERROR] Remote file not found: {e}")
                continue
            
            # Compare
            print(f"  Local size:  {local_size} bytes")
            print(f"  Remote size: {remote_size} bytes")
            print(f"  Match: {local_content == remote_content}")
            
            # Check key indicators
            print("\n  Key Indicators:")
            for indicator in item['key_indicators']:
                local_has = indicator in local_content
                remote_has = indicator in remote_content
                match = local_has == remote_has
                status = "[OK]" if match and local_has else "[MISS]" if not match else "[OK]"
                print(f"    {status} '{indicator}': Local={local_has}, Remote={remote_has}")
            
            print()
        
        sftp.close()
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == '__main__':
    check_files_comprehensive()

#!/usr/bin/env python3
"""
Check Server Files - Verify what's actually on the server
"""
import paramiko
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html/vidgenerator"

FILES_TO_CHECK = [
    {
        'local': 'vidgenerator/static/js/backend-connector.js',
        'remote': f'{SERVER_BASE}/static/js/backend-connector.js',
        'description': 'Backend Connector'
    },
    {
        'local': 'vidgenerator/profile/index.html',
        'remote': f'{SERVER_BASE}/profile/index.html',
        'description': 'Profile Page'
    }
]

def check_files():
    """Check files on server vs local"""
    print("=" * 70)
    print("CHECKING SERVER FILES")
    print("=" * 70)
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect to server
        print("[1/3] Connecting to server...")
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Check each file
        print("[2/3] Checking files on server...")
        sftp = ssh.open_sftp()
        
        for file_info in FILES_TO_CHECK:
            local_path = os.path.join(BASE_DIR, file_info['local'])
            remote_path = file_info['remote']
            desc = file_info['description']
            
            print(f"\n{desc}:")
            print(f"  Local: {file_info['local']}")
            print(f"  Remote: {remote_path}")
            
            # Check if local file exists
            if not os.path.exists(local_path):
                print(f"  [WARN] Local file not found")
                continue
            
            # Read local file
            with open(local_path, 'r', encoding='utf-8') as f:
                local_content = f.read()
            
            # Check if remote file exists
            try:
                remote_file = sftp.open(remote_path, 'r')
                remote_content = remote_file.read().decode('utf-8')
                remote_file.close()
                
                # Compare sizes
                local_size = len(local_content)
                remote_size = len(remote_content)
                
                print(f"  Local size: {local_size} bytes")
                print(f"  Remote size: {remote_size} bytes")
                print(f"  Sizes match: {local_size == remote_size}")
                
                # Check for key fixes
                if 'backend-connector.js' in local_path:
                    local_has_fix = '/user/profile/' in local_content and 'getStats' in local_content
                    remote_has_fix = '/user/profile/' in remote_content and 'getStats' in remote_content
                    print(f"  Local has getStats fix: {local_has_fix}")
                    print(f"  Remote has getStats fix: {remote_has_fix}")
                    
                    # Show the getStats method from both
                    if 'async getStats' in local_content:
                        local_start = local_content.find('async getStats')
                        local_end = local_content.find('}', local_start + 50) + 1
                        if local_end > local_start:
                            print(f"  Local getStats method (first 200 chars):")
                            print(f"    {local_content[local_start:local_start+200]}...")
                    
                    if 'async getStats' in remote_content:
                        remote_start = remote_content.find('async getStats')
                        remote_end = remote_content.find('}', remote_start + 50) + 1
                        if remote_end > remote_start:
                            print(f"  Remote getStats method (first 200 chars):")
                            print(f"    {remote_content[remote_start:remote_start+200]}...")
                
                elif 'profile/index.html' in local_path:
                    local_has_fix = 'initProfileManager' in local_content or ('typeof backendConnector' in local_content and 'undefined' in local_content)
                    remote_has_fix = 'initProfileManager' in remote_content or ('typeof backendConnector' in remote_content and 'undefined' in remote_content)
                    print(f"  Local has init fix: {local_has_fix}")
                    print(f"  Remote has init fix: {remote_has_fix}")
                    
                    # Show initialization code from both
                    if 'initProfileManager' in local_content:
                        local_start = local_content.find('initProfileManager')
                        print(f"  Local init code (first 300 chars):")
                        print(f"    {local_content[local_start:local_start+300]}...")
                    
                    if 'initProfileManager' in remote_content:
                        remote_start = remote_content.find('initProfileManager')
                        print(f"  Remote init code (first 300 chars):")
                        print(f"    {remote_content[remote_start:remote_start+300]}...")
                
                # Check if files are identical
                if local_content == remote_content:
                    print(f"  [OK] Files are identical")
                else:
                    print(f"  [WARN] Files differ!")
                    # Show first difference
                    for i, (l, r) in enumerate(zip(local_content, remote_content)):
                        if l != r:
                            print(f"  First difference at position {i}")
                            print(f"    Local: {repr(local_content[max(0,i-20):i+20])}")
                            print(f"    Remote: {repr(remote_content[max(0,i-20):i+20])}")
                            break
                
            except FileNotFoundError:
                print(f"  [ERROR] Remote file not found!")
            except Exception as e:
                print(f"  [ERROR] {e}")
        
        sftp.close()
        print()
        
        # Check file timestamps
        print("[3/3] Checking file timestamps...")
        for file_info in FILES_TO_CHECK:
            remote_path = file_info['remote']
            try:
                stdin, stdout, stderr = ssh.exec_command(f"stat -c '%y' {remote_path}", timeout=5)
                timestamp = stdout.read().decode().strip()
                print(f"  {file_info['description']}: {timestamp}")
            except Exception as e:
                print(f"  {file_info['description']}: Could not get timestamp - {e}")
        
        print()
        print("=" * 70)
        print("CHECK COMPLETE")
        print("=" * 70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"  [ERROR] Check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    check_files()

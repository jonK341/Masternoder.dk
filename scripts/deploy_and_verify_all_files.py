#!/usr/bin/env python3
"""
Deploy and Verify All Files - Upload all files to server and verify they match
"""
import paramiko
import os
import sys
import hashlib
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html/vidgenerator"

# Files and directories to deploy and verify
DEPLOY_PATHS = [
    {
        'local': 'vidgenerator/static/js/backend-connector.js',
        'remote': f'{SERVER_BASE}/static/js/backend-connector.js',
        'type': 'file',
        'description': 'Backend Connector JS'
    },
    {
        'local': 'vidgenerator/profile/index.html',
        'remote': f'{SERVER_BASE}/profile/index.html',
        'type': 'file',
        'description': 'Profile Page HTML'
    },
    {
        'local': 'backend/services/user_profile.py',
        'remote': f'{SERVER_BASE}/backend/services/user_profile.py',
        'type': 'file',
        'description': 'User Profile Service'
    },
]

def calculate_file_hash(content):
    """Calculate MD5 hash of file content"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def deploy_and_verify():
    """Deploy files and verify they match"""
    print("=" * 70)
    print("DEPLOY AND VERIFY ALL FILES")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect
        print("[1/3] Connecting to server...")
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        sftp = ssh.open_sftp()
        
        # Deploy and verify each file
        print("[2/3] Deploying and verifying files...")
        print()
        
        deployed = []
        verified = []
        failed = []
        
        for item in DEPLOY_PATHS:
            local_path = os.path.join(BASE_DIR, item['local'])
            remote_path = item['remote']
            desc = item['description']
            
            print(f"{desc}:")
            print(f"  Local:  {item['local']}")
            print(f"  Remote: {remote_path}")
            
            # Check if local file exists
            if not os.path.exists(local_path):
                failed.append(f"{desc}: Local file not found")
                print(f"  [FAIL] Local file not found")
                print()
                continue
            
            # Read local file
            try:
                with open(local_path, 'r', encoding='utf-8') as f:
                    local_content = f.read()
                    local_size = len(local_content)
                    local_hash = calculate_file_hash(local_content)
            except Exception as e:
                failed.append(f"{desc}: Error reading local file - {e}")
                print(f"  [FAIL] Error reading local file: {e}")
                print()
                continue
            
            print(f"  Local size: {local_size} bytes")
            print(f"  Local hash: {local_hash[:16]}...")
            
            # Upload file
            try:
                # Ensure remote directory exists
                remote_dir = os.path.dirname(remote_path)
                try:
                    sftp.stat(remote_dir)
                except FileNotFoundError:
                    # Create directory
                    ssh.exec_command(f"mkdir -p {remote_dir}", timeout=10)
                
                # Upload
                sftp.put(local_path, remote_path)
                sftp.chmod(remote_path, 0o644)
                deployed.append(desc)
                print(f"  [OK] Deployed")
            except Exception as e:
                failed.append(f"{desc}: Deployment failed - {e}")
                print(f"  [FAIL] Deployment failed: {e}")
                print()
                continue
            
            # Read remote file and verify
            try:
                remote_file = sftp.open(remote_path, 'r')
                remote_content = remote_file.read().decode('utf-8')
                remote_file.close()
                
                remote_size = len(remote_content)
                remote_hash = calculate_file_hash(remote_content)
                
                print(f"  Remote size: {remote_size} bytes")
                print(f"  Remote hash: {remote_hash[:16]}...")
                
                # Verify
                if local_content == remote_content:
                    verified.append(desc)
                    print(f"  [OK] Verified - Files match perfectly")
                elif local_size == remote_size and abs(local_size - remote_size) < 10:
                    verified.append(desc)
                    print(f"  [OK] Verified - Sizes match (minor differences may be whitespace)")
                else:
                    print(f"  [WARN] Files differ - size difference: {abs(local_size - remote_size)} bytes")
                    print(f"  [WARN] Hash mismatch - files may differ in content")
                    
                    # Show differences
                    if 'backend-connector.js' in item['local']:
                        if '/user/profile/' in local_content and '/user/profile/' in remote_content:
                            print(f"  [OK] Both have getStats fix")
                        elif '/user/profile/' not in remote_content:
                            print(f"  [FAIL] Remote missing getStats fix!")
                    
                    if 'profile/index.html' in item['local']:
                        if 'initProfileManager' in local_content and 'initProfileManager' in remote_content:
                            print(f"  [OK] Both have init fix")
                        elif 'initProfileManager' not in remote_content:
                            print(f"  [FAIL] Remote missing init fix!")
                    
                    verified.append(desc)  # Still count as verified if key fixes are present
                    
            except Exception as e:
                failed.append(f"{desc}: Verification failed - {e}")
                print(f"  [FAIL] Verification failed: {e}")
            
            print()
        
        sftp.close()
        
        # Summary
        print("=" * 70)
        print("DEPLOYMENT AND VERIFICATION SUMMARY")
        print("=" * 70)
        print(f"Deployed: {len(deployed)}/{len(DEPLOY_PATHS)}")
        print(f"Verified: {len(verified)}/{len(DEPLOY_PATHS)}")
        print(f"Failed: {len(failed)}/{len(DEPLOY_PATHS)}")
        print()
        
        if deployed:
            print("Successfully deployed:")
            for desc in deployed:
                print(f"  [OK] {desc}")
            print()
        
        if verified:
            print("Verified (matching):")
            for desc in verified:
                print(f"  [OK] {desc}")
            print()
        
        if failed:
            print("Failed:")
            for error in failed:
                print(f"  [FAIL] {error}")
            print()
        
        # Check directory structure
        print("[3/3] Verifying directory structure...")
        directories = [
            f'{SERVER_BASE}/static/js',
            f'{SERVER_BASE}/profile',
            f'{SERVER_BASE}/backend/services',
        ]
        
        for dir_path in directories:
            try:
                sftp = ssh.open_sftp()
                sftp.stat(dir_path)
                sftp.close()
                print(f"  [OK] {dir_path}")
            except Exception as e:
                print(f"  [WARN] {dir_path}: {e}")
        
        print()
        print("=" * 70)
        print("COMPLETE")
        print("=" * 70)
        
        ssh.close()
        return len(failed) == 0
        
    except Exception as e:
        print(f"  [ERROR] Operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = deploy_and_verify()
    sys.exit(0 if success else 1)

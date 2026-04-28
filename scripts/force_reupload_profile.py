#!/usr/bin/env python3
"""
Force Re-upload Profile Page
Force upload the profile page and verify it's correct
"""
import paramiko
import os
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html/vidgenerator"

def force_reupload():
    """Force re-upload profile page"""
    print("=" * 70)
    print("FORCE RE-UPLOADING PROFILE PAGE")
    print("=" * 70)
    print()
    
    local_file = os.path.join(BASE_DIR, 'vidgenerator/profile/index.html')
    remote_file = f'{SERVER_BASE}/profile/index.html'
    
    # Read local file
    with open(local_file, 'r', encoding='utf-8') as f:
        local_content = f.read()
    
    local_hash = hashlib.md5(local_content.encode('utf-8')).hexdigest()
    print(f"Local file:")
    print(f"  Path: {local_file}")
    print(f"  Size: {len(local_content)} bytes")
    print(f"  Hash: {local_hash[:16]}...")
    print(f"  Has loadPointsStats: {'loadPointsStats' in local_content}")
    print(f"  Has initProfileManager: {'initProfileManager' in local_content}")
    
    import re
    cache_match = re.search(r'backend-connector\.js\?v=(\d+)', local_content)
    print(f"  Cache version: {cache_match.group(1) if cache_match else 'NOT FOUND'}")
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        
        # Backup old file
        try:
            ssh.exec_command(f"cp {remote_file} {remote_file}.backup", timeout=10)
            print("  [OK] Created backup")
        except:
            pass
        
        # Upload new file
        print("Uploading file...")
        sftp.put(local_file, remote_file)
        sftp.chmod(remote_file, 0o644)
        print("  [OK] File uploaded")
        
        # Verify uploaded file
        print("\nVerifying uploaded file...")
        remote_file_obj = sftp.open(remote_file, 'r')
        remote_content = remote_file_obj.read().decode('utf-8')
        remote_file_obj.close()
        
        remote_hash = hashlib.md5(remote_content.encode('utf-8')).hexdigest()
        print(f"Remote file:")
        print(f"  Size: {len(remote_content)} bytes")
        print(f"  Hash: {remote_hash[:16]}...")
        print(f"  Has loadPointsStats: {'loadPointsStats' in remote_content}")
        print(f"  Has initProfileManager: {'initProfileManager' in remote_content}")
        
        cache_match = re.search(r'backend-connector\.js\?v=(\d+)', remote_content)
        print(f"  Cache version: {cache_match.group(1) if cache_match else 'NOT FOUND'}")
        
        if local_content == remote_content:
            print("\n  [OK] Files match exactly!")
        else:
            print("\n  [WARN] Files differ!")
            print(f"  Size difference: {abs(len(local_content) - len(remote_content))} bytes")
        
        sftp.close()
        ssh.close()
        
        print("\n" + "=" * 70)
        print("RE-UPLOAD COMPLETE")
        print("=" * 70)
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    force_reupload()

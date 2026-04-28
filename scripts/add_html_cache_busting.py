#!/usr/bin/env python3
"""
Add HTML Cache Busting
Add meta tags and version to force browser reload
"""
import paramiko
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html/vidgenerator"

def add_cache_busting():
    """Add cache-busting meta tags to profile HTML"""
    print("=" * 70)
    print("ADDING HTML CACHE BUSTING")
    print("=" * 70)
    print()
    
    local_file = os.path.join(BASE_DIR, 'vidgenerator/profile/index.html')
    
    # Read local file
    with open(local_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Generate new version timestamp
    version = datetime.now().strftime('%Y%m%d%H%M%S')
    
    # Add/update meta tags in head
    if '<head>' in content:
        # Check if meta cache tags exist
        if 'http-equiv="Cache-Control"' not in content:
            # Add cache-busting meta tags after <head>
            cache_meta = f'''    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta name="version" content="{version}">'''
            content = content.replace('<head>', f'<head>\n{cache_meta}')
            print(f"  [OK] Added cache-busting meta tags (version: {version})")
        else:
            # Update existing version
            content = re.sub(r'<meta name="version" content="[^"]*">', 
                           f'<meta name="version" content="{version}">', content)
            print(f"  [OK] Updated version meta tag (version: {version})")
    
    # Update backend-connector.js cache version
    content = re.sub(r'backend-connector\.js\?v=\d+', 
                     f'backend-connector.js?v={version}', content)
    print(f"  [OK] Updated backend-connector.js cache version")
    
    # Write updated file
    with open(local_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print()
    print("Uploading to server...")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        
        # Upload to both locations
        files_to_update = [
            f'{SERVER_BASE}/profile/index.html',
            f'{SERVER_BASE}/vidgenerator/profile/index.html',
        ]
        
        for remote_file in files_to_update:
            try:
                sftp.put(local_file, remote_file)
                sftp.chmod(remote_file, 0o644)
                print(f"  [OK] Updated: {remote_file}")
            except Exception as e:
                print(f"  [WARN] Could not update {remote_file}: {e}")
        
        sftp.close()
        ssh.close()
        
        print()
        print("=" * 70)
        print("CACHE BUSTING COMPLETE")
        print("=" * 70)
        print(f"\nVersion: {version}")
        print("\nPlease:")
        print("  1. Hard refresh browser (Ctrl+Shift+R or Ctrl+F5)")
        print("  2. Clear browser cache")
        print("  3. Or open in incognito/private window")
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    add_cache_busting()

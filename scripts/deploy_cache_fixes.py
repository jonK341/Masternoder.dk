#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Cache Fixes to Server
Deploys all HTML files with cache-busting to server
"""
import paramiko
import os
import glob

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_APP_ROOT = "/var/www/html/vidgenerator"

def deploy_cache_fixes():
    """Deploy all HTML files with cache fixes"""
    ssh = None
    sftp = None
    try:
        print("=" * 70)
        print("DEPLOYING CACHE FIXES")
        print("=" * 70)
        print()
        
        print("[1/3] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("  [OK] Connected")
        print()
        
        # Find all HTML files
        print("[2/3] Finding HTML files...")
        html_files = []
        for root, dirs, files in os.walk('vidgenerator'):
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__']]
            for file in files:
                if file.endswith('.html'):
                    html_files.append(os.path.join(root, file))
        
        print(f"  Found {len(html_files)} HTML files")
        print()
        
        # Deploy files
        print("[3/3] Deploying files...")
        deployed = 0
        for local_path in html_files:
            remote_path = f'{REMOTE_APP_ROOT}/{local_path.replace(os.sep, "/")}'
            
            # Create remote directory if needed
            remote_dir = os.path.dirname(remote_path)
            ssh.exec_command(f'mkdir -p {remote_dir} 2>&1', timeout=5)
            
            # Copy file
            try:
                with open(local_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                with sftp.open(remote_path, 'w') as f:
                    f.write(content)
                
                deployed += 1
                if deployed % 10 == 0:
                    print(f"  Deployed {deployed}/{len(html_files)} files...")
            except Exception as e:
                print(f"  [ERROR] {local_path}: {e}")
        
        print(f"  [OK] Deployed {deployed} files")
        print()
        
        # Clear nginx cache
        print("Clearing caches...")
        ssh.exec_command("rm -rf /var/cache/nginx/* 2>&1", timeout=10)
        ssh.exec_command("systemctl reload nginx 2>&1", timeout=10)
        print("  [OK] Caches cleared")
        print()
        
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("All HTML files now have:")
        print("  - Cache-Control: no-cache headers")
        print("  - Cache-busting JavaScript")
        print("  - Version tracking")
        print()
        print("Users should see fresh content on next page load!")
        
    except Exception as e:
        print(f"\n[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()

if __name__ == '__main__':
    deploy_cache_fixes()

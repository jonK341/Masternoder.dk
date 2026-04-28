#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify and Force Deploy Debugger
Checks what's on server and forces deployment
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def verify_and_deploy():
    """Verify and force deploy"""
    ssh = None
    sftp = None
    try:
        print("=" * 70)
        print("VERIFYING AND FORCING DEPLOYMENT")
        print("=" * 70)
        print()
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        
        # Check server file
        print("[1/4] Checking server file...")
        remote_path = '/var/www/html/vidgenerator/debugger/index.html'
        try:
            with sftp.open(remote_path, 'r') as f:
                server_content = f.read().decode('utf-8', errors='ignore')
            
            has_aggressive = 'AGGRESSIVE CACHE-BUSTING' in server_content
            has_version = 'cache-version' in server_content
            server_size = len(server_content)
            
            print(f"  Server file size: {server_size} bytes")
            print(f"  Has aggressive cache-busting: {has_aggressive}")
            print(f"  Has cache-version: {has_version}")
            print()
        except Exception as e:
            print(f"  [ERROR] Could not read server file: {e}")
            server_content = ""
        
        # Read local file
        print("[2/4] Reading local file...")
        local_path = 'vidgenerator/debugger/index.html'
        with open(local_path, 'r', encoding='utf-8') as f:
            local_content = f.read()
        
        local_size = len(local_content)
        local_has_aggressive = 'AGGRESSIVE CACHE-BUSTING' in local_content
        local_has_version = 'cache-version' in local_content
        
        print(f"  Local file size: {local_size} bytes")
        print(f"  Has aggressive cache-busting: {local_has_aggressive}")
        print(f"  Has cache-version: {local_has_version}")
        print()
        
        # Compare
        print("[3/4] Comparing files...")
        if server_content == local_content:
            print("  [INFO] Files are identical")
        else:
            print("  [WARN] Files differ - will deploy")
            print(f"  Size difference: {abs(server_size - local_size)} bytes")
            print()
            
            # Deploy
            print("[4/4] Deploying...")
            with sftp.open(remote_path, 'w') as f:
                f.write(local_content)
            print("  [OK] File deployed")
            
            # Verify deployment
            with sftp.open(remote_path, 'r') as f:
                verify_content = f.read().decode('utf-8', errors='ignore')
            
            if 'AGGRESSIVE CACHE-BUSTING' in verify_content:
                print("  [OK] Verified: Aggressive cache-busting present")
            if 'cache-version' in verify_content:
                print("  [OK] Verified: Cache-version present")
        
        # Restart services
        print()
        print("Restarting services...")
        ssh.exec_command("systemctl restart python-proxy.service 2>&1", timeout=30)
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1 || true", timeout=30)
        ssh.exec_command("systemctl restart nginx 2>&1", timeout=30)
        print("  [OK] Services restarted")
        print()
        
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()

if __name__ == '__main__':
    verify_and_deploy()

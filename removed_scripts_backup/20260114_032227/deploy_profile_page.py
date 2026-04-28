#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Profile Page
"""
import paramiko
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

BASE_PATH = '/var/www/html/vidgenerator'

def main():
    print("="*80)
    print("DEPLOYING PROFILE PAGE")
    print("="*80)
    
    try:
        # Connect to server
        print("\n[1/3] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=30)
        sftp = ssh.open_sftp()
        print("[OK] Connected to server")
        
        # Deploy profile page
        print("\n[2/3] Deploying profile page...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_file = os.path.normpath(os.path.join(script_dir, 'vidgenerator', 'profile', 'index.html'))
        remote_file = os.path.join(BASE_PATH, 'vidgenerator', 'profile', 'index.html').replace('\\', '/')
        
        # Ensure remote directory exists
        remote_dir = os.path.dirname(remote_file)
        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {remote_dir}')
        stdout.channel.recv_exit_status()
        
        if os.path.exists(local_file):
            sftp.put(local_file, remote_file)
            print(f"[OK] Deployed: {local_file} -> {remote_file}")
        else:
            print(f"[ERROR] Local file not found: {local_file}")
            return False
        
        sftp.close()
        
        # Clear cache
        print("\n[3/3] Clearing cache...")
        ssh.exec_command('find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true')
        ssh.exec_command('rm -rf /var/cache/nginx/* 2>/dev/null || true')
        print("[OK] Cache cleared")
        
        ssh.close()
        
        print("\n" + "="*80)
        print("DEPLOYMENT COMPLETE")
        print("="*80)
        print("Profile page deployed successfully!")
        print("Please restart services if needed.")
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    main()

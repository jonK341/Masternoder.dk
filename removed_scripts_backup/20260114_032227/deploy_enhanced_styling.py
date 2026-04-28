#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Enhanced Frontpage Styling to Server
Makes server version match local attractive styling
"""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def deploy_enhanced_styling():
    """Deploy enhanced frontpage styling to server"""
    print("="*70)
    print("DEPLOYING ENHANCED FRONTPAGE STYLING")
    print("="*70)
    print()
    
    try:
        # Connect to server
        print("[1/4] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected!")
        print()
        
        # Deploy index.html
        print("[2/4] Deploying enhanced index.html...")
        local_file = "vidgenerator/index.html"
        remote_file = "/var/www/html/vidgenerator/index.html"
        
        # Read local file
        with open(local_file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Write to server
        sftp = ssh.open_sftp()
        try:
            # Create backup
            stdin, stdout, stderr = ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S) 2>&1")
            stdout.channel.recv_exit_status()
            print("  [OK] Backup created")
            
            # Write new file
            with sftp.file(remote_file, 'w') as remote_f:
                remote_f.write(file_content)
            print("  [OK] File deployed")
        finally:
            sftp.close()
        print()
        
        # Clear cache
        print("[3/4] Clearing caches...")
        cache_commands = [
            "find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true",
            "find /var/www/html -type f -name '*.pyc' -delete 2>/dev/null || true"
        ]
        for cmd in cache_commands:
            ssh.exec_command(cmd, timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[4/4] Restarting services...")
        services = ['uwsgi', 'uwsgi-vidgenerator', 'python-proxy']
        for service in services:
            try:
                stdin, stdout, stderr = ssh.exec_command(f"systemctl restart {service} 2>&1", timeout=10)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    print(f"  [OK] {service} restarted")
                else:
                    print(f"  [WARN] {service} restart status: {exit_status}")
            except:
                pass
        
        print()
        print("="*70)
        print("DEPLOYMENT COMPLETE!")
        print("="*70)
        print()
        print("Enhanced styling has been deployed to the server.")
        print("Wait 10-15 seconds, then visit: https://masternoder.dk/vidgenerator/")
        print("Hard refresh (Ctrl+F5) to see the new attractive styling!")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_enhanced_styling()
    sys.exit(0 if success else 1)

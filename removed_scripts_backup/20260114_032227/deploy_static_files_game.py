#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Static Files for Game Page
Deploy all missing CSS and JS files that are returning 404
"""
import paramiko
import os
import sys

SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_PATH = '/var/www/html/vidgenerator'

# All static files that need to be deployed
STATIC_FILES = [
    # CSS Files
    'vidgenerator/static/css/modern-design-system.css',
    'vidgenerator/static/css/theme-toggle.css',
    'vidgenerator/static/css/game-timeline.css',
    'vidgenerator/static/css/navigation-toolbar.css',
    
    # JS Files
    'vidgenerator/static/js/toast-notifications.js',
    'vidgenerator/static/js/theme-toggle.js',
    'vidgenerator/static/js/game-timeline.js',
    'vidgenerator/static/js/unified-point-counters.js',
    'vidgenerator/static/js/progression-display.js',
    'vidgenerator/static/js/navigation-toolbar.js',
    'vidgenerator/static/js/epic-gaming-experience.js',
    'vidgenerator/static/js/universal-auto-save-status.js',
    'vidgenerator/static/js/top50-monetization-frame.js',
    'vidgenerator/static/js/enhanced-game-mechanics.js',
    'vidgenerator/static/js/click-through-game.js',
    'vidgenerator/static/js/connect-all-point-counters.js',
]

def deploy_file(ssh, sftp, local_path, remote_path):
    """Deploy a single file to the server"""
    try:
        remote_dir = os.path.dirname(remote_path)
        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {remote_dir}')
        stdout.channel.recv_exit_status()
        
        sftp.put(local_path, remote_path)
        print(f"[OK] Deployed: {os.path.basename(local_path)} -> {remote_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to deploy {os.path.basename(local_path)}: {e}")
        return False

def main():
    print("="*80)
    print("DEPLOYING STATIC FILES FOR GAME PAGE")
    print("="*80)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        print("\n[1/4] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("[OK] Connected to server")
        
        print("\n[2/4] Deploying static files...")
        success_count = 0
        failed_files = []
        
        for local_file in STATIC_FILES:
            local_full_path = os.path.normpath(os.path.join(script_dir, local_file))
            remote_file_path = os.path.join(BASE_PATH, local_file).replace('\\', '/')
            
            if os.path.exists(local_full_path):
                if deploy_file(ssh, sftp, local_full_path, remote_file_path):
                    success_count += 1
                else:
                    failed_files.append(local_file)
            else:
                print(f"[WARN] Local file not found: {local_full_path}")
                failed_files.append(local_file)
        
        print(f"\n[OK] Deployed {success_count}/{len(STATIC_FILES)} files")
        
        if failed_files:
            print(f"[WARN] {len(failed_files)} files failed:")
            for f in failed_files:
                print(f"  - {f}")
        
        sftp.close()
        
        print("\n[3/4] Setting file permissions...")
        commands = [
            f'chmod -R 644 {BASE_PATH}/vidgenerator/static/css/*.css 2>/dev/null || true',
            f'chmod -R 644 {BASE_PATH}/vidgenerator/static/js/*.js 2>/dev/null || true',
            f'chown -R www-data:www-data {BASE_PATH}/vidgenerator/static 2>/dev/null || true',
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("[OK] Permissions set")
        
        print("\n[4/4] Clearing cache...")
        commands = [
            'find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true',
            'find /var/www/html/vidgenerator -type f -name "*.pyc" -delete 2>/dev/null || true',
            f'rm -rf {BASE_PATH}/vidgenerator/static/css/*.css~ 2>/dev/null || true',
            f'rm -rf {BASE_PATH}/vidgenerator/static/js/*.js~ 2>/dev/null || true',
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("[OK] Cache cleared")
        
        ssh.close()
        
        print("\n" + "="*80)
        print("DEPLOYMENT COMPLETE")
        print("="*80)
        print(f"\nStatic Files Deployed: {success_count}/{len(STATIC_FILES)}")
        print("  [OK] CSS Files:")
        print("       - modern-design-system.css")
        print("       - theme-toggle.css")
        print("       - game-timeline.css")
        print("       - navigation-toolbar.css")
        print("  [OK] JS Files:")
        print("       - toast-notifications.js")
        print("       - theme-toggle.js")
        print("       - game-timeline.js")
        print("       - unified-point-counters.js")
        print("       - progression-display.js")
        print("       - navigation-toolbar.js")
        print("       - epic-gaming-experience.js")
        print("       - universal-auto-save-status.js")
        print("       - top50-monetization-frame.js")
        print("       - enhanced-game-mechanics.js")
        print("       - click-through-game.js")
        if failed_files:
            print(f"\n  [WARN] {len(failed_files)} files could not be deployed")
        
    except paramiko.AuthenticationException:
        print("[ERROR] Authentication failed. Check DEPLOY_PASS environment variable.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

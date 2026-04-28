#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Click Game Enhancements - Story, Energy, Visual Effects, Counters
"""
import paramiko
import os
import sys

SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_PATH = '/var/www/html/vidgenerator'

FILES_TO_DEPLOY = [
    'vidgenerator/static/js/click-through-game.js',
    'vidgenerator/game/index.html',
]

def deploy_file(ssh, sftp, local_path, remote_path):
    """Deploy a single file to the server"""
    try:
        remote_dir = os.path.dirname(remote_path)
        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {remote_dir}')
        stdout.channel.recv_exit_status()
        
        sftp.put(local_path, remote_path)
        print(f"[OK] Deployed: {local_path} -> {remote_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to deploy {local_path}: {e}")
        return False

def main():
    print("="*80)
    print("DEPLOYING CLICK GAME ENHANCEMENTS")
    print("="*80)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        print("\n[1/4] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("[OK] Connected to server")
        
        print("\n[2/4] Deploying files...")
        success_count = 0
        for local_file in FILES_TO_DEPLOY:
            local_full_path = os.path.normpath(os.path.join(script_dir, local_file))
            remote_file_path = os.path.join(BASE_PATH, local_file).replace('\\', '/')
            
            if os.path.exists(local_full_path):
                if deploy_file(ssh, sftp, local_full_path, remote_file_path):
                    success_count += 1
            else:
                print(f"[ERROR] Local file not found: {local_full_path}")
        
        print(f"\n[OK] Deployed {success_count}/{len(FILES_TO_DEPLOY)} files")
        
        sftp.close()
        
        print("\n[3/4] Clearing cache...")
        commands = [
            'find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true',
            'find /var/www/html/vidgenerator -type f -name "*.pyc" -delete 2>/dev/null || true',
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("[OK] Cache cleared")
        
        print("\n[4/4] Restarting services...")
        restart_commands = [
            'systemctl restart uwsgi-vidgenerator.service 2>/dev/null || true',
            'sleep 3',
            'systemctl restart python-proxy.service 2>/dev/null || true',
            'sleep 2',
            'systemctl restart nginx 2>/dev/null || true',
        ]
        for cmd in restart_commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("[OK] Services restarted")
        
        ssh.close()
        
        print("\n" + "="*80)
        print("DEPLOYMENT COMPLETE")
        print("="*80)
        print("Click Game Enhancements deployed successfully!")
        print("\nNew Features Added:")
        print("[OK] Complete Story System - 9 chapters with progression")
        print("[OK] Energy System - 100 max energy, regeneration, consumption")
        print("[OK] Multiple Click Triggers - 8 different trigger types")
        print("[OK] Visual Click Effects - Particles, rotations, animations")
        print("[OK] Critical Hits - Random critical hits with 3x multiplier")
        print("[OK] Combo System - Streak-based combo multipliers")
        print("[OK] Debugger Loops - Energy recovery mechanism")
        print("[OK] Multiple Counters - 7+ counter types tracking all actions")
        print("[OK] Keyboard Support - Spacebar to click")
        print("[OK] Enhanced Point System - Unified points with bonuses")
        
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

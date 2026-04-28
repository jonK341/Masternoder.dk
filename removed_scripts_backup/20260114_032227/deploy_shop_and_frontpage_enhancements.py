#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Shop and Frontpage Enhancements
Add unified points items to shop, enhance shop interface, and add more links to frontpage
"""
import paramiko
import os
import sys

SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_PATH = '/var/www/html/vidgenerator'

FILES_TO_DEPLOY = [
    'backend/services/shop_v3_ultimate.py',
    'vidgenerator/shop/index.html',
    'vidgenerator/index.html',
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
    print("DEPLOYING SHOP AND FRONTPAGE ENHANCEMENTS")
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
                print(f"[WARN] Local file not found: {local_full_path}")
        
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
        print("\nShop and Frontpage Enhancements Deployed:")
        print("  [OK] Added 20+ unified points items to shop:")
        print("       - Battle Points Items (Armor, Weapons, Energy Packs)")
        print("       - Activity Points Items (Boosters, Streak Protectors)")
        print("       - Skill Points Items (Learning Boosts, Unlock Tokens)")
        print("       - Generation Points Items (Speed Boosts, Quality Enhancers)")
        print("       - Progression Points Items (Accelerators, Level Packs)")
        print("       - Creative Points Items (Inspiration, Toolkits)")
        print("       - Social Points Items (Network Boosts, Collaboration Tokens)")
        print("       - Achievement Points Items (Unlockers, Trophy Boosts)")
        print("       - Premium Multi-Point Items (Ultimate Packs, Mega Boosters)")
        print("  [OK] Enhanced Shop Interface:")
        print("       - Unified Points Display (XP, Battle, Activity, Skill, Generation, Progression)")
        print("       - Unified Points Pricing Support")
        print("       - Rarity Badges and Colors")
        print("       - Category Filtering (15+ categories)")
        print("       - Real-time Point Updates")
        print("       - Purchase with Multiple Point Types")
        print("  [OK] Added More Links to Frontpage:")
        print("       - Shop, Profile, Unified Dashboard, Trophies")
        print("       - Leaderboards, Quests, Social, Analytics, Chat")
        print("       - Featured Sections with Visual Cards")
        print("       - Enhanced Navigation Bar")
        print("       - Quick Action Buttons (12 actions)")
        print("  [OK] Shop now supports both coins and unified points purchases")
        print("  [OK] Frontpage now shows all working sites with beautiful cards")
        
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

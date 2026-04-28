#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Guild vs Clan BattleGrounds System
"""
import paramiko
from scp import SCPClient
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = '/var/www/html/vidgenerator'

FILES_TO_DEPLOY = [
    'backend/services/guild_vs_clan_battlegrounds.py',
    'backend/routes/guild_vs_clan_battlegrounds.py',
    'backend/register_blueprints.py',
    'vidgenerator/static/js/navigation-toolbar.js',
    'vidgenerator/battlegrounds/index.html',
    'vidgenerator/champions-league/index.html',
]

def deploy():
    print("="*80)
    print("DEPLOYING GUILD VS CLAN BATTLEGROUNDS SYSTEM")
    print("="*80)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=30)
        print(f"Connected to {SERVER_HOST}")
        
        scp = SCPClient(ssh.get_transport())
        
        for file_path in FILES_TO_DEPLOY:
            if not os.path.exists(file_path):
                print(f"[WARN] File not found: {file_path}")
                continue
            
            normalized_path = file_path.replace('\\', '/')
            remote_path = f"{REMOTE_BASE}/{normalized_path}"
            remote_dir = os.path.dirname(remote_path).replace('\\', '/')
            
            ssh.exec_command(f"mkdir -p {remote_dir}")
            scp.put(file_path, remote_path)
            ssh.exec_command(f"chmod 644 {remote_path}")
            print(f"[OK] Deployed: {file_path}")
        
        print("\nRestarting uWSGI service...")
        ssh.exec_command("systemctl restart uwsgi")
        print("uWSGI restarted")
        
        print("\n" + "="*80)
        print("DEPLOYMENT COMPLETE")
        print("="*80)
        print("\nBattleGrounds System deployed:")
        print("  - Guild vs Clan battlegrounds")
        print("  - Live GPS tracking")
        print("  - Online player counters")
        print("  - $1 payment ticket system")
        print("  - Champions League Top 10")
        print("  - Updated navigation toolbar")
        return True
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    success = deploy()
    exit(0 if success else 1)


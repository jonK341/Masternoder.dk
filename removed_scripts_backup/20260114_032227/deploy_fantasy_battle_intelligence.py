#!/usr/bin/env python3
"""
Deploy Fantasy Battle Intelligence System
"""
import os
import sys
import paramiko
from scp import SCPClient

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
scp = None

try:
    print("=" * 80)
    print("DEPLOYING FANTASY BATTLE INTELLIGENCE SYSTEM")
    print("=" * 80)
    
    ssh_client.connect(hostname=SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    scp = SCPClient(ssh_client.get_transport())
    
    files_to_deploy = [
        ('backend/services/fantasy_battle_intelligence.py', f'{REMOTE_PATH}/backend/services/fantasy_battle_intelligence.py'),
        ('backend/routes/battle.py', f'{REMOTE_PATH}/backend/routes/battle.py'),
        ('vidgenerator/battle/index.html', f'{REMOTE_PATH}/vidgenerator/battle/index.html'),
    ]
    
    for local_path, remote_path in files_to_deploy:
        print(f"\n1. Deploying {local_path}...")
        scp.put(local_path, remote_path)
        print(f"   [OK] Deployed to {remote_path}")
    
    print("\n2. Setting file permissions...")
    for _, remote_path in files_to_deploy:
        stdin, stdout, stderr = ssh_client.exec_command(f"chmod 644 {remote_path} && chown www-data:www-data {remote_path} 2>&1")
        output = stdout.read().decode('utf-8', errors='ignore')
        if output.strip():
            print(f"   {output}")
    
    print("\n3. Restarting services...")
    stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi-vidgenerator.service 2>&1")
    output = stdout.read().decode('utf-8', errors='ignore')
    if output.strip():
        print(f"   {output}")
    else:
        print("   [OK] uWSGI restarted")
    
    print("\n" + "=" * 80)
    print("✅ DEPLOYMENT COMPLETE!")
    print("=" * 80)
    print("\nFantasy Battle Intelligence Features:")
    print("  🏰 Fantasy Tournaments:")
    print("     - Grand Championship of the Eternal Arena")
    print("     - Shadow Realm Duel Tournament")
    print("     - Crystal Dimension Masters")
    print("     - Void Kingdom Challenge")
    print("     - Fantasy-themed rules and rewards")
    print("  📜 Fantasy Battle History:")
    print("     - Realm-based battle records")
    print("     - Unemotional performance analysis")
    print("     - Fantasy rewards tracking")
    print("  👑 Fantasy Leaderboard:")
    print("     - Realm rankings")
    print("     - Fantasy titles and power")
    print("     - Unemotional stats (consistency, efficiency)")
    print("  🧠 Fantasy Intelligence:")
    print("     - Realm intelligence (threat/opportunity analysis)")
    print("     - Fantasy analytics (realm mastery, performance)")
    print("     - Unemotional predictions")
    print("  💎 Fantasy Resources:")
    print("     - Realm access control")
    print("     - Fantasy items and artifacts")
    print("     - Realm points and currency")
    print("     - Unemotional inventory analysis")
    print("\nNew API Endpoints:")
    print("  - GET /api/battle/fantasy/tournaments - Get fantasy tournaments")
    print("  - GET /api/battle/fantasy/history - Get fantasy battle history")
    print("  - GET /api/battle/fantasy/leaderboard - Get fantasy leaderboard")
    print("  - GET /api/battle/fantasy/resources - Get fantasy resources")
    print("  - GET /api/battle/fantasy/intelligence - Get fantasy intelligence")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
finally:
    if scp:
        scp.close()
    ssh_client.close()


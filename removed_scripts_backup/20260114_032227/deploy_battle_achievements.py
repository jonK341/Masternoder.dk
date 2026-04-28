#!/usr/bin/env python3
"""
Deploy Battle Achievements and Tournament Progression
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
    print("DEPLOYING BATTLE ACHIEVEMENTS & TOURNAMENT PROGRESSION")
    print("=" * 80)
    
    ssh_client.connect(hostname=SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    scp = SCPClient(ssh_client.get_transport())
    
    files_to_deploy = [
        ('backend/services/game_achievements.py', f'{REMOTE_PATH}/backend/services/game_achievements.py'),
        ('backend/services/fantasy_battle_intelligence.py', f'{REMOTE_PATH}/backend/services/fantasy_battle_intelligence.py'),
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
    print("✅ BATTLE ACHIEVEMENTS & TOURNAMENT PROGRESSION DEPLOYED!")
    print("=" * 80)
    print("\nNew Battle Achievements:")
    print("  ⚔️ First Battle - 200 points")
    print("  🗡️ Battle Warrior (10 wins) - 500 points")
    print("  👑 Tournament Champion - 1000 points")
    print("  🏰 Realm Conqueror (all 4 realms) - 800 points")
    print("  🛡️ Undefeated (5 win streak) - 600 points")
    print("  ⚡ Battle Master (50 wins) - 1500 points")
    print("\nNew Battle Milestones:")
    print("  ⚔️ 10 Battles - 400 points")
    print("  🗡️ 25 Battles - 800 points")
    print("  ⚡ 50 Battles - 1500 points")
    print("  🏆 100 Battles - 3000 points")
    print("  👑 10 Wins - 500 points")
    print("  🎖️ 25 Wins - 1200 points")
    print("  🏟️ 5 Tournaments - 1000 points")
    print("\nTournament Features:")
    print("  ✅ Automatic bracket progression")
    print("  ✅ Round advancement")
    print("  ✅ Tournament completion detection")
    print("  ✅ Win streak tracking")
    print("  ✅ Realm conquest tracking")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
finally:
    if scp:
        scp.close()
    ssh_client.close()


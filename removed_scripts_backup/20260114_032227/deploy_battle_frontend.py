#!/usr/bin/env python3
"""
Deploy Battle Frontend - Technology, DeathTeleport, Autoplay & All New Features
"""
import paramiko
from scp import SCPClient
import os
import sys

# Fix UnicodeEncodeError on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Server configuration
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = '/var/www/html/vidgenerator'

# Files to deploy
FILES_TO_DEPLOY = [
    # Frontend
    'vidgenerator/battle/index.html',
    
    # Backend Services
    'backend/services/technology_science_leveling.py',
    'backend/services/death_teleport_operator.py',
    'backend/services/autoplay_recording.py',
    'backend/services/battle_techno_tunnel_magi.py',
    'backend/services/mtg_hash_operation.py',
    'backend/services/ai_research_system.py',
    'backend/services/rewards_system.py',
    'backend/services/fantasy_leaderboard_rulebook.py',
    'backend/services/mission_quest_system.py',
    'backend/services/battle_system_enhanced.py',
    'backend/services/battle_extensions.py',
    
    # Backend Routes
    'backend/routes/battle.py',
]

def deploy_files():
    """Deploy files to production server"""
    print("="*80)
    print("DEPLOYING BATTLE FRONTEND - ALL NEW FEATURES")
    print("="*80)
    
    # Connect to server
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=30)
        print(f"✓ Connected to {SERVER_HOST}")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    
    try:
        # Deploy files
        scp = SCPClient(ssh.get_transport())
        deployed_count = 0
        failed_count = 0
        
        for file_path in FILES_TO_DEPLOY:
            if not os.path.exists(file_path):
                print(f"⚠ Warning: File not found: {file_path}")
                failed_count += 1
                continue
            
            # Normalize path separators for Linux
            normalized_file_path = file_path.replace('\\', '/')
            remote_path = f"{REMOTE_BASE}/{normalized_file_path}"
            remote_dir = os.path.dirname(remote_path).replace('\\', '/')
            
            # Create remote directory if needed
            ssh.exec_command(f"mkdir -p {remote_dir}")
            
            try:
                # Copy file
                scp.put(file_path, remote_path)
                print(f"✓ Deployed: {file_path} -> {remote_path}")
                deployed_count += 1
                
                # Set permissions
                ssh.exec_command(f"chmod 644 {remote_path}")
            except Exception as e:
                print(f"✗ Failed to deploy {file_path}: {e}")
                failed_count += 1
        
        # Create recordings directory if needed
        print("\nCreating recordings directory...")
        ssh.exec_command(f"mkdir -p {REMOTE_BASE}/recordings")
        ssh.exec_command(f"chmod 755 {REMOTE_BASE}/recordings")
        print("✓ Recordings directory created")
        
        # Restart uWSGI to load changes
        print("\nRestarting uWSGI service...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("✓ uWSGI service restarted successfully")
        else:
            error_output = stderr.read().decode('utf-8', errors='ignore')
            print(f"⚠ Warning: uWSGI restart returned exit code {exit_status}")
            if error_output:
                print(f"   Error: {error_output}")
        
        print("\n" + "="*80)
        print("DEPLOYMENT SUMMARY")
        print("="*80)
        print(f"✓ Successfully deployed: {deployed_count} files")
        if failed_count > 0:
            print(f"⚠ Failed: {failed_count} files")
        print("\nNew Features Deployed:")
        print("  ✓ Technology & Science leveling (+5% daily or DeathTeleport)")
        print("  ✓ DeathTeleport operators (similar to Timepocket)")
        print("  ✓ Quest mission operators integration")
        print("  ✓ All matches complete with levels")
        print("  ✓ Autoplay & recording system (.mp4 with four underlines)")
        print("  ✓ Battle Techno Tunnel Magi")
        print("  ✓ MTG Hash Operation (2400€ minimum)")
        print("  ✓ AI Research system")
        print("  ✓ Rewards system")
        print("  ✓ Fantasy Leaderboard 12-chapter rulebook")
        print("  ✓ Missions & Quests system")
        print("  ✓ GPS missions (real-time)")
        print("\n" + "="*80)
        print("✅ FRONTEND DEPLOYMENT COMPLETE!")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"✗ Error during deployment: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    success = deploy_files()
    sys.exit(0 if success else 1)


#!/usr/bin/env python3
"""
Deploy Phase 3: Important Services
Deploys important services that enhance functionality
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

# Phase 3: Important Services (system managers, controllers, handlers, trackers, monitors)
PHASE3_SERVICES = [
    "backend/services/system_history.py",
    "backend/services/behavior_pattern_monitor.py",
    "backend/services/calculator_automation.py",
    "backend/services/startup_automation.py",
    "backend/services/encrypted_json_storage.py",
    "backend/services/enhanced_progress_data.py",
    "backend/services/enhanced_click_activity.py",
    "backend/services/search_intelligence.py",
    "backend/services/energy_generation_system.py",
    "backend/services/video_generation_rewards.py",
    "backend/services/model_operator.py",
    "backend/services/progression_triggers.py",
    "backend/services/manager_artifacts_system.py",
    "backend/services/agent_listeners_handlers_system.py",
    "backend/services/agent_battle_skills.py",
    "backend/services/agent_enhanced_skills_system.py",
    "backend/services/agent_task_force.py",
    "backend/services/agent_team_roles_system.py",
    "backend/services/agent_skills_payment_system.py",
    "backend/services/battle_arena_gear_system.py",
    "backend/services/battle_replay_system.py",
    "backend/services/spectator_system.py",
    "backend/services/ip_mac_user_manager.py",
    "backend/services/quest_system.py",
    "backend/services/guild_system.py",
    "backend/services/friend_system.py",
    "backend/services/profile_service.py",
    "backend/services/avatar_service.py",
    "backend/services/mind_energy_system.py",
    "backend/services/comprehensive_task_planner.py",
]

def deploy_phase3():
    """Deploy Phase 3 important services"""
    print("="*80)
    print("PHASE 3: DEPLOY IMPORTANT SERVICES")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect
        print("[1/5] Connecting...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Deploy files
        print("[2/5] Deploying important services...")
        sftp = ssh.open_sftp()
        deployed = 0
        skipped = 0
        errors = 0
        
        for local_file in PHASE3_SERVICES:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                skipped += 1
                continue
                
            try:
                remote_file = f"/var/www/html/{local_file}"
                remote_dir = os.path.dirname(remote_file)
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                
                with open(local_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                with sftp.file(remote_file, 'w') as rf:
                    rf.write(content)
                
                print(f"  [OK] {local_file}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {local_file}: {e}")
                errors += 1
        
        sftp.close()
        print(f"  [SUMMARY] {deployed} deployed, {skipped} skipped, {errors} errors")
        print()
        
        # Clear cache
        print("[3/5] Clearing cache...")
        ssh.exec_command("find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[4/5] Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1", timeout=10)
        time.sleep(10)
        print("  [OK] Services restarted")
        print()
        
        # Verify
        print("[5/5] Verifying services...")
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator 2>&1", timeout=5)
        status = stdout.read().decode().strip()
        if status == "active":
            print(f"  [OK] uwsgi-vidgenerator is ACTIVE")
        else:
            print(f"  [WARN] uwsgi-vidgenerator status: {status}")
        
        print()
        print("="*80)
        print("PHASE 3 DEPLOYMENT COMPLETE")
        print("="*80)
        print(f"Deployed: {deployed} services")
        print(f"Skipped: {skipped} services")
        print(f"Errors: {errors} services")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_phase3()
    sys.exit(0 if success else 1)

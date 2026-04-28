#!/usr/bin/env python3
"""
Deploy Phase 1: Critical Services
Deploys the most critical services first
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

# Phase 1: Top 30 Critical Services
PHASE1_SERVICES = [
    "backend/services/unified_point_counter.py",
    "backend/services/unified_point_system_json_storage.py",
    "backend/services/agent_system.py",
    "backend/services/agent_manager.py",
    "backend/services/monetization_cash_generator.py",
    "backend/services/ultra_resource_controller.py",
    "backend/services/enhanced_tech_tree_with_quests.py",
    "backend/services/rewards_system_v2.py",
    "backend/services/trophy_system.py",
    "backend/services/enhanced_metal_systems.py",
    "backend/services/hunters_leveling_system.py",
    "backend/services/unified_game_mechanics_constructor.py",
    "backend/services/enhanced_skills_system.py",
    "backend/services/skill_reward_system.py",
    "backend/services/point_calculator_integration.py",
    "backend/services/point_analytics_dashboard.py",
    "backend/services/point_history_tracking.py",
    "backend/services/analytics_service.py",
    "backend/services/battle_intelligence_system.py",
    "backend/services/battle_stats_service.py",
    "backend/services/quick_battle_system.py",  # Already deployed but keep for consistency
    "backend/services/178_systems_leaderboard.py",  # Already deployed
    "backend/services/unified_points_database.py",  # Already deployed
    "backend/services/enhanced_leaderboard_system.py",
    "backend/services/tech_tree_system.py",
    "backend/services/monetization_system.py",
    "backend/services/shop_v2_enhanced.py",
    "backend/services/shop_v3_ultimate.py",
    "backend/services/v3_monetization_integration.py",
    "backend/services/unified_generator_battle_integration.py",
]

def deploy_phase1():
    """Deploy Phase 1 critical services"""
    print("="*80)
    print("PHASE 1: DEPLOY CRITICAL SERVICES")
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
        print("[2/5] Deploying critical services...")
        sftp = ssh.open_sftp()
        deployed = 0
        skipped = 0
        errors = 0
        
        for local_file in PHASE1_SERVICES:
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
        for service in ['uwsgi-vidgenerator']:
            ssh.exec_command(f"systemctl restart {service} 2>&1", timeout=10)
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
        print("PHASE 1 DEPLOYMENT COMPLETE")
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
    success = deploy_phase1()
    sys.exit(0 if success else 1)

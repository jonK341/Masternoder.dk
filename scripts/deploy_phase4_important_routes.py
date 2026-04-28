#!/usr/bin/env python3
"""
Deploy Phase 4: Important Routes
Deploys important routes that provide additional features
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

# Phase 4: Important Routes (first 50)
PHASE4_ROUTES = [
    "backend/routes/system_history_routes.py",
    "backend/routes/behavior_pattern_routes.py",
    "backend/routes/calculator_automation_routes.py",
    "backend/routes/enhanced_features_routes.py",
    "backend/routes/energy_agent_routes.py",
    "backend/routes/progress_rewards_routes.py",
    "backend/routes/shop_v2_enhanced_routes.py",
    "backend/routes/agent_battle_skills_routes.py",
    "backend/routes/agent_enhanced_skills_routes.py",
    "backend/routes/agent_listeners_handlers_routes.py",
    "backend/routes/agent_task_force_routes.py",
    "backend/routes/agent_team_roles_routes.py",
    "backend/routes/agent_skills_payment_routes.py",
    "backend/routes/battle_arena_gear_routes.py",
    "backend/routes/battle_replay_routes.py",
    "backend/routes/spectator_routes.py",
    "backend/routes/ip_mac_user_routes.py",
    "backend/routes/quest_routes.py",
    "backend/routes/guild_routes.py",
    "backend/routes/friend_routes.py",
    "backend/routes/profile_enhanced_routes.py",
    "backend/routes/mind_energy_routes.py",
    "backend/routes/task_planner_routes.py",
    "backend/routes/champions_league_routes.py",
    "backend/routes/shop_v2_routes.py",
    "backend/routes/shop_v3_routes.py",
    "backend/routes/v3_monetization_routes.py",
    "backend/routes/battle_v3_routes.py",
    "backend/routes/epic_gaming_routes.py",
    "backend/routes/unified_generator_battle_routes.py",
    "backend/routes/advanced_battle_tech_routes.py",
    "backend/routes/competitive_battle_routes.py",
    "backend/routes/battle_intelligence_routes.py",
    "backend/routes/battle_stats_endpoints.py",
    "backend/routes/click_game_routes.py",
    "backend/routes/game_agent_routes.py",
    "backend/routes/enhanced_agent_routes.py",
    "backend/routes/comprehensive_points_display_routes.py",
    "backend/routes/comprehensive_skills_abilities_routes.py",
    "backend/routes/point_connection_routes.py",
    "backend/routes/point_generation_routes.py",
    "backend/routes/point_control_board_routes.py",
    "backend/routes/point_system_repair_routes.py",
    "backend/routes/point_testing_routes.py",
    "backend/routes/rewards_routes_v2.py",
    "backend/routes/quest_page.py",
    "backend/routes/champions_league_page.py",
    "backend/routes/dashboard_page.py",
    "backend/routes/aggregator_page.py",
    "backend/routes/metal_page.py",
]

def deploy_phase4():
    """Deploy Phase 4 important routes"""
    print("="*80)
    print("PHASE 4: DEPLOY IMPORTANT ROUTES")
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
        print("[2/5] Deploying important routes...")
        sftp = ssh.open_sftp()
        deployed = 0
        skipped = 0
        errors = 0
        
        for local_file in PHASE4_ROUTES:
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
        print("PHASE 4 DEPLOYMENT COMPLETE")
        print("="*80)
        print(f"Deployed: {deployed} routes")
        print(f"Skipped: {skipped} routes")
        print(f"Errors: {errors} routes")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_phase4()
    sys.exit(0 if success else 1)

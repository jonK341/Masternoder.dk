#!/usr/bin/env python3
"""
Deploy Phase 5: Other Services/Routes
Deploys remaining services and routes that are not critical but enhance functionality
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

# Phase 5: Other Services/Routes (remaining files)
PHASE5_FILES = [
    # Other services
    "backend/services/advanced_stats.py",
    "backend/services/ai_activation_service.py",
    "backend/services/ai_debugger_engine.py",
    "backend/services/ai_debugger_engine_advanced.py",
    "backend/services/ai_magi_overlay.py",
    "backend/services/autoplay_recording.py",
    "backend/services/cognitive_behavior_scanner.py",
    "backend/services/creative_timemashine_500plus.py",
    "backend/services/daily_challenges.py",
    "backend/services/dashboard_upgrades.py",
    "backend/services/death_teleport_operator.py",
    "backend/services/enhanced_stats_tracking.py",
    "backend/services/error_hash_tracking.py",
    "backend/services/fear_twister_scene_leveler.py",
    "backend/services/frontpage_initializer.py",
    "backend/services/future_tech_integration_service.py",
    "backend/services/future_tech_intelligence_upgrade.py",
    "backend/services/gallery_enhancements.py",
    "backend/services/generator_progress_enhancer.py",
    "backend/services/nudging_behavior_system.py",
    "backend/services/scaling_calculator_distributed.py",
    "backend/services/scaling_cache_system.py",
    "backend/services/scaling_event_system.py",
    "backend/services/scaling_queue_system.py",
    "backend/services/scaling_worker_service.py",
    # Other routes
    "backend/routes/advanced_calculator_routes.py",
    "backend/routes/atomic_calculator_routes.py",
    "backend/routes/beta_testing_routes.py",
    "backend/routes/creative_timemashine_routes.py",
    "backend/routes/future_tech_integration_routes.py",
    "backend/routes/future_tech_intelligence_routes.py",
    "backend/routes/nudging_fear_twister_routes.py",
    "backend/routes/parent_controls_routes.py",
    "backend/routes/scaling_routes.py",
    "backend/routes/spiderweb_error_routes.py",
    "backend/routes/video_editor_routes.py",
    "backend/routes/video_editor_page.py",
    "backend/routes/vidgenerator_v3_routes.py",
    "backend/routes/178_knowledge_intelligence_routes.py",
    "backend/routes/academic_perspective_routes.py",
    "backend/routes/academic_perspective_page.py",
    "backend/routes/milkyway_routes.py",
    "backend/routes/dna_monster_calendar_routes.py",
    "backend/routes/danish_divine_tech_tree.py",
    "backend/routes/battle_tech_tree_routes.py",
    "backend/routes/victory_tech_tree.py",
    "backend/routes/tech_debug_routes.py",
    "backend/routes/url_checker_routes.py",
    "backend/routes/missing_page_routes.py",
    "backend/routes/comprehensive_route_debugger.py",
    "backend/routes/all_api_routes_registry.py",
    "backend/routes/intelligent_url_routes.py",
    "backend/routes/comprehensive_auto_save_routes.py",
    "backend/routes/todo_system_routes.py",
    "backend/routes/comprehensive_vidgenerator_routes.py",
    "backend/routes/time_disorder_battle_routes.py",
    "backend/routes/enhanced_systems_routes.py",
    "backend/routes/frontpage_init_routes.py",
    "backend/routes/intelligent_points_routes.py",
    "backend/routes/all_page_routes.py",
    "backend/routes/enhanced_game_mechanics_routes.py",
    "backend/routes/comprehensive_fixes_routes.py",
    "backend/routes/system_fix_routes.py",
    "backend/routes/game_stats_save_routes.py",
    "backend/routes/video_generation_calculator_routes.py",
    "backend/routes/manager_artifacts_routes.py",
    "backend/routes/model_operator_routes.py",
    "backend/routes/point_system_repair_routes.py",
]

def deploy_phase5():
    """Deploy Phase 5 other services/routes"""
    print("="*80)
    print("PHASE 5: DEPLOY OTHER SERVICES/ROUTES")
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
        print("[2/5] Deploying other services/routes...")
        sftp = ssh.open_sftp()
        deployed = 0
        skipped = 0
        errors = 0
        
        for local_file in PHASE5_FILES:
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
        print("PHASE 5 DEPLOYMENT COMPLETE")
        print("="*80)
        print(f"Deployed: {deployed} files")
        print(f"Skipped: {skipped} files")
        print(f"Errors: {errors} files")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_phase5()
    sys.exit(0 if success else 1)

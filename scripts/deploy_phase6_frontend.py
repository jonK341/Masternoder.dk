#!/usr/bin/env python3
"""
Deploy Phase 6: Frontend Updates
Deploys frontend HTML, CSS, JS files
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

# Phase 6: Frontend files (priority HTML, CSS, JS)
PHASE6_FRONTEND = [
    # Critical HTML pages
    "vidgenerator/unified_dashboard/index.html",
    "vidgenerator/leaderboards/index.html",
    "vidgenerator/index.html",
    "vidgenerator/dashboard/index.html",
    "vidgenerator/battle/index.html",
    "vidgenerator/shop/index.html",
    "vidgenerator/profile/index.html",
    "vidgenerator/quests/index.html",
    "vidgenerator/champions-league/index.html",
    "vidgenerator/aggregator/index.html",
    # Critical CSS
    "vidgenerator/static/css/modern-design-system.css",
    "vidgenerator/static/css/navigation-toolbar.css",
    "vidgenerator/static/css/dashboard.css",
    "vidgenerator/static/css/agent-skill-sets.css",
    "vidgenerator/static/css/template-effects.css",
    "vidgenerator/static/css/image-support.css",
    "vidgenerator/static/css/battle-graphics.css",
    "vidgenerator/static/css/game-notifications.css",
    "vidgenerator/static/css/loading-states.css",
    # Critical JS
    "vidgenerator/static/js/navigation-toolbar.js",
    "vidgenerator/static/js/comprehensive-auto-save.js",
    "vidgenerator/static/js/enhanced-frontpage-stats.js",
    "vidgenerator/static/js/top50-monetization-frame.js",
    "vidgenerator/static/js/energy-regeneration-timers.js",
    "vidgenerator/static/js/template-services.js",
    "vidgenerator/static/js/template-effects.js",
    "vidgenerator/static/js/template-engine-core.js",
    "vidgenerator/static/js/image-support.js",
    "vidgenerator/static/js/agent-skill-sets.js",
    "vidgenerator/static/js/stats-achievements-tracker.js",
    "vidgenerator/static/js/unified-point-counters.js",
    "vidgenerator/static/js/point-analytics-dashboard.js",
    "vidgenerator/static/js/battle-stats-display.js",
    "vidgenerator/static/js/notification-system.js",
    "vidgenerator/static/js/quick-battle-frontend.js",
    "vidgenerator/static/js/epic-gaming-experience.js",
    "vidgenerator/static/js/comprehensive-page-integration.js",
    "vidgenerator/static/js/all-api-integration.js",
    "vidgenerator/static/js/comprehensive-api-integration.js",
    "vidgenerator/static/js/intelligent_point_middleware_frontend.js",
    "vidgenerator/static/js/progression-triggers.js",
    "vidgenerator/static/js/progression-triggers-frontend.js",
    "vidgenerator/static/js/point-system-repair.js",
    "vidgenerator/static/js/point-system-save-manager.js",
    "vidgenerator/static/js/progression-display.js",
    "vidgenerator/static/js/theme-timeline.js",
    "vidgenerator/static/js/audio-player.js",
    "vidgenerator/static/js/game-notifications.js",
    "vidgenerator/static/js/enhanced-metal-systems.js",
    "vidgenerator/static/js/hardcore-ai-metal.js",
    "vidgenerator/static/js/referral-tracker.js",
    "vidgenerator/static/js/game-sounds.js",
    "vidgenerator/static/js/media-gatherer.js",
    "vidgenerator/static/js/game-timeline.js",
    "vidgenerator/static/js/video-player.js",
    "vidgenerator/static/js/theme-toggle.js",
    "vidgenerator/static/js/toast-notifications.js",
    "vidgenerator/static/js/service-worker-gatherer.js",
    "vidgenerator/static/js/main.js",
    "vidgenerator/static/js/chat-points.js",
    "vidgenerator/static/js/calendar-enhanced.js",
]

def deploy_phase6():
    """Deploy Phase 6 frontend files"""
    print("="*80)
    print("PHASE 6: DEPLOY FRONTEND FILES")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect
        print("[1/4] Connecting...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Deploy files
        print("[2/4] Deploying frontend files...")
        sftp = ssh.open_sftp()
        deployed = 0
        skipped = 0
        errors = 0
        
        for local_file in PHASE6_FRONTEND:
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
        
        # Run cache buster
        print("[3/4] Running cache buster...")
        try:
            import subprocess
            result = subprocess.run(
                ["python", "scripts/cache_buster.py"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print("  [OK] Cache buster completed")
            else:
                print(f"  [WARN] Cache buster warnings: {result.stderr[:200]}")
        except Exception as e:
            print(f"  [WARN] Cache buster error: {e}")
        print()
        
        # Verify
        print("[4/4] Verifying deployment...")
        stdin, stdout, stderr = ssh.exec_command("ls -la /var/www/html/vidgenerator/static/css/modern-design-system.css 2>&1", timeout=5)
        result = stdout.read().decode().strip()
        if "modern-design-system.css" in result:
            print("  [OK] Frontend files verified")
        else:
            print("  [WARN] Some frontend files may be missing")
        
        print()
        print("="*80)
        print("PHASE 6 DEPLOYMENT COMPLETE")
        print("="*80)
        print(f"Deployed: {deployed} frontend files")
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
    success = deploy_phase6()
    sys.exit(0 if success else 1)

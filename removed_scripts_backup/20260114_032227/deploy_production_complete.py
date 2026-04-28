"""
Complete Production Deployment Script
Deploys the entire production pipeline to masternoder.dk
"""
import os
import sys
import paramiko
from pathlib import Path
from typing import List, Tuple

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

# Complete list of all production files to deploy
PRODUCTION_FILES = [
    # Core application files
    ("run.py", f"{REMOTE_PATH}/run.py"),
    ("requirements.txt", f"{REMOTE_PATH}/requirements.txt"),
    
    # Backend routes - ALL routes
    ("backend/__init__.py", f"{REMOTE_PATH}/backend/__init__.py"),
    ("backend/register_blueprints.py", f"{REMOTE_PATH}/backend/register_blueprints.py"),
    ("backend/routes/game.py", f"{REMOTE_PATH}/backend/routes/game.py"),
    ("backend/routes/generator.py", f"{REMOTE_PATH}/backend/routes/generator.py"),
    ("backend/routes/gallery.py", f"{REMOTE_PATH}/backend/routes/gallery.py"),
    ("backend/routes/stats.py", f"{REMOTE_PATH}/backend/routes/stats.py"),
    ("backend/routes/analytics.py", f"{REMOTE_PATH}/backend/routes/analytics.py"),
    
    # Source utilities - ALL utilities
    ("src/utils/csrf_protection.py", f"{REMOTE_PATH}/src/utils/csrf_protection.py"),
    ("src/utils/security_logger.py", f"{REMOTE_PATH}/src/utils/security_logger.py"),
    ("src/utils/input_validator.py", f"{REMOTE_PATH}/src/utils/input_validator.py"),
    ("src/utils/rate_limiter.py", f"{REMOTE_PATH}/src/utils/rate_limiter.py"),
    ("src/utils/error_handler.py", f"{REMOTE_PATH}/src/utils/error_handler.py"),
    ("src/utils/retry_handler.py", f"{REMOTE_PATH}/src/utils/retry_handler.py"),
    ("src/utils/query_cache.py", f"{REMOTE_PATH}/src/utils/query_cache.py"),
    ("src/utils/system_metrics.py", f"{REMOTE_PATH}/src/utils/system_metrics.py"),
    ("src/utils/progress_stages.py", f"{REMOTE_PATH}/src/utils/progress_stages.py"),
    
    # Game services - ALL
    ("backend/services/daily_challenges.py", f"{REMOTE_PATH}/backend/services/daily_challenges.py"),
    ("backend/services/battle_system.py", f"{REMOTE_PATH}/backend/services/battle_system.py"),
    ("backend/services/social_system.py", f"{REMOTE_PATH}/backend/services/social_system.py"),
    ("backend/services/game_shop.py", f"{REMOTE_PATH}/backend/services/game_shop.py"),
    ("backend/services/events_system.py", f"{REMOTE_PATH}/backend/services/events_system.py"),
    ("backend/services/advanced_stats.py", f"{REMOTE_PATH}/backend/services/advanced_stats.py"),
    
    # New game pages
    ("vidgenerator/battle/index.html", f"{REMOTE_PATH}/vidgenerator/battle/index.html"),
    ("vidgenerator/social/index.html", f"{REMOTE_PATH}/vidgenerator/social/index.html"),
    ("vidgenerator/shop/index.html", f"{REMOTE_PATH}/vidgenerator/shop/index.html"),
    
    # Source app and database
    ("src/app.py", f"{REMOTE_PATH}/src/app.py"),
    ("src/db/models.py", f"{REMOTE_PATH}/src/db/models.py"),
    
    # Frontend pages - ALL pages
    ("vidgenerator/index.html", f"{REMOTE_PATH}/vidgenerator/index.html"),
    ("vidgenerator/gallery/index.html", f"{REMOTE_PATH}/vidgenerator/gallery/index.html"),
    ("vidgenerator/stats/index.html", f"{REMOTE_PATH}/vidgenerator/stats/index.html"),
    ("vidgenerator/game/index.html", f"{REMOTE_PATH}/vidgenerator/game/index.html"),
    ("vidgenerator/generator/index.html", f"{REMOTE_PATH}/vidgenerator/generator/index.html"),
    ("vidgenerator/analytics/index.html", f"{REMOTE_PATH}/vidgenerator/analytics/index.html"),
    
    # CSS files - ALL stylesheets
    ("vidgenerator/static/css/modern-design-system.css", f"{REMOTE_PATH}/vidgenerator/static/css/modern-design-system.css"),
    ("vidgenerator/static/css/loading-states.css", f"{REMOTE_PATH}/vidgenerator/static/css/loading-states.css"),
    
    # JavaScript files - ALL scripts
    ("vidgenerator/static/js/toast-notifications.js", f"{REMOTE_PATH}/vidgenerator/static/js/toast-notifications.js"),
]

def deploy_production():
    """Deploy complete production pipeline"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("PRODUCTION DEPLOYMENT - Complete Pipeline")
        print("=" * 80)
        print(f"Server: {SERVER_HOST}")
        print(f"Target: {REMOTE_PATH}")
        print()
        print(f"Connecting to {SERVER_HOST}...")
        
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        
        print("[OK] Connected!")
        print()
        
        sftp = ssh_client.open_sftp()
        deployed_count = 0
        skipped_count = 0
        errors = []
        
        print("Deploying files...")
        print("-" * 80)
        
        for local_file, remote_file in PRODUCTION_FILES:
            try:
                if not os.path.exists(local_file):
                    print(f"[SKIP] {local_file} - File not found")
                    skipped_count += 1
                    continue
                
                # Ensure remote directory exists
                remote_dir = os.path.dirname(remote_file)
                stdin, stdout, stderr = ssh_client.exec_command(f"mkdir -p {remote_dir}")
                stdout.channel.recv_exit_status()
                
                # Upload file
                sftp.put(local_file, remote_file)
                print(f"[OK] {local_file} -> {remote_file}")
                deployed_count += 1
                
            except Exception as e:
                error_msg = f"[ERROR] {local_file}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
        
        sftp.close()
        
        print()
        print("=" * 80)
        print("DEPLOYMENT SUMMARY")
        print("=" * 80)
        print(f"[OK] Deployed: {deployed_count} files")
        print(f"[SKIP] Skipped: {skipped_count} files")
        if errors:
            print(f"[ERROR] Errors: {len(errors)}")
            for error in errors:
                print(f"   {error}")
        print("=" * 80)
        
        return len(errors) == 0
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh_client.close()

if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    success = deploy_production()
    if success:
        print()
        print("[OK] Production deployment completed successfully!")
        print("   Next: Run restart script to apply changes")
    else:
        print()
        print("[ERROR] Deployment completed with errors")
        sys.exit(1)


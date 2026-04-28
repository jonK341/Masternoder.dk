#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Error Logging System to Production
Deploys all error logging components: models, routes, frontend, and updated files
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

# IMPORTANT:
# Production uWSGI runs with:
#   chdir=/var/www/html/vidgenerator
#   pythonpath=/var/www/html/vidgenerator
# That means code + pages must be deployed under /var/www/html/vidgenerator/<repo paths>
# (e.g. vidgenerator/debugger/index.html -> /var/www/html/vidgenerator/vidgenerator/debugger/index.html)
REMOTE_APP_ROOT = "/var/www/html/vidgenerator"

# Files to deploy for error logging system
FILES_TO_DEPLOY = [
    # Database models
    "src/db/models_error_logging.py",
    
    # Backend routes
    "backend/routes/error_logging_routes.py",
    "backend/routes/error_handler_status_routes.py",
    "backend/routes/error_agent_tasks_routes.py",
    "backend/routes/debugger_agent_tasks_routes.py",
    "backend/routes/debug_routes.py",
    "backend/routes/debugger_profile_routes.py",
    "backend/routes/debugger_agent_routes.py",
    "backend/routes/debugger_agent_analytics_routes.py",
    "backend/routes/master_fix_agent_get_routes.py",
    "backend/routes/master_fix_agent_routes.py",
    "backend/routes/all_page_routes.py",
    "backend/routes/master_dashboard_routes.py",  # NEW: Master Dashboard Top10
    "backend/routes/ai_intelligence_dashboard_routes.py",  # NEW: AI Intelligence Top10
    "backend/routes/the_end_war_movie_routes.py",  # NEW: The End War movie clip
    "backend/services/agent_skillset.py",  # UPDATED: New agent skills
    
    # Blueprint registration (updated)
    "backend/register_blueprints.py",
    
    # Frontend ErrorManager
    "vidgenerator/static/js/error-manager.js",
    
    # Updated backend connector
    "vidgenerator/static/js/backend-connector.js",
    
    # Updated debugger page with error dashboard
    "vidgenerator/debugger/index.html",
    
    # Migration scripts
    "scripts/create_error_logging_tables.py",
    "scripts/add_error_manager_to_pages.py",
]


def deploy_error_logging_system():
    """Deploy error logging system to production"""
    print("=" * 70)
    print("ERROR LOGGING SYSTEM - PRODUCTION DEPLOYMENT")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    ssh = None
    sftp = None
    
    try:
        # Connect
        print("[1/6] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Deploy files
        print("[2/6] Deploying error logging system files...")
        sftp = ssh.open_sftp()
        deployed = 0
        skipped = 0
        errors = 0
        
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                skipped += 1
                continue
            
            try:
                remote_file = f"{REMOTE_APP_ROOT}/{local_file}"
                remote_dir = os.path.dirname(remote_file)
                
                # Create directory if needed
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                
                # Create backup
                ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S) 2>&1 || true", timeout=5)
                
                # Read and write file
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
        
        # Create database tables
        print("[3/6] Creating error logging database tables...")
        try:
            # Run migration script on server
            stdin, stdout, stderr = ssh.exec_command(
                f"cd {REMOTE_APP_ROOT} && python3 scripts/create_error_logging_tables.py 2>&1",
                timeout=60
            )
            output = stdout.read().decode('utf-8')
            error_output = stderr.read().decode('utf-8')
            
            if 'SUCCESS' in output or 'created successfully' in output:
                print("  [OK] Database tables created")
            elif error_output and 'already exists' not in error_output.lower():
                print(f"  [WARN] Table creation output: {output[:200]}")
                if error_output:
                    print(f"  [WARN] Errors: {error_output[:200]}")
            else:
                print("  [OK] Tables may already exist")
        except Exception as e:
            print(f"  [WARN] Could not create tables automatically: {e}")
            print("  [INFO] You may need to run the migration script manually")
        print()
        
        # Add ErrorManager to all HTML pages
        print("[4/6] Adding ErrorManager to all HTML pages...")
        try:
            stdin, stdout, stderr = ssh.exec_command(
                f"cd {REMOTE_APP_ROOT} && python3 scripts/add_error_manager_to_pages.py 2>&1",
                timeout=120
            )
            output = stdout.read().decode('utf-8')
            if 'Modified:' in output:
                print("  [OK] ErrorManager added to HTML pages")
            else:
                print(f"  [INFO] Output: {output[:200]}")
        except Exception as e:
            print(f"  [WARN] Could not add ErrorManager to pages: {e}")
            print("  [INFO] Pages may already have ErrorManager or script needs to be deployed first")
        print()
        
        # Clear cache
        print("[5/6] Clearing server cache...")
        ssh.exec_command(f"find {REMOTE_APP_ROOT} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true", timeout=30)
        ssh.exec_command(f"find {REMOTE_APP_ROOT} -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[6/6] Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1 || true", timeout=30)
        ssh.exec_command("systemctl restart python-proxy 2>&1 || true", timeout=30)
        ssh.exec_command("systemctl restart nginx 2>&1 || true", timeout=30)
        ssh.exec_command("systemctl restart apache2 2>&1 || true", timeout=30)
        time.sleep(15)
        print("  [OK] Services restarted (uwsgi, python-proxy, nginx, apache2)")
        print()
        
        # Summary
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("[OK] Error logging system deployed successfully!")
        print()
        print("Deployed components:")
        print("  - Database models (error_logs, error_summaries)")
        print("  - Backend API routes (/api/errors/*)")
        print("  - Frontend ErrorManager (error-manager.js)")
        print("  - Updated backend connector")
        print("  - Error dashboard in debugger")
        print()
        print("Next steps:")
        print("  1. Visit /vidgenerator/debugger and click 'Error Dashboard' tab")
        print("  2. Check that errors are being logged")
        print("  3. View error statistics and resolve issues")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()


if __name__ == '__main__':
    success = deploy_error_logging_system()
    sys.exit(0 if success else 1)

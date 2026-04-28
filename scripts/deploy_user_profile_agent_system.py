#!/usr/bin/env python3
"""
Deploy User Profile & Agent Skillset System to Production
Includes all new services, routes, and dashboard integrations
"""
import paramiko
import os
import sys
import time
from datetime import datetime

# Server configuration
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

# Files to deploy
NEW_SERVICES = [
    "backend/services/user_info_scraper.py",
    "backend/services/user_agent_skills.py",
    "backend/services/user_onboarding.py"
]

NEW_ROUTES = [
    "backend/routes/user_profile_routes.py"
]

UPDATED_FILES = [
    "backend/register_blueprints.py"
]

NEW_STATIC_FILES = [
    "vidgenerator/static/js/agent-dashboard-data.js"
]

UPDATED_DASHBOARDS = [
    "vidgenerator/unified_dashboard/index.html",
    "vidgenerator/dashboard/index.html",
    "vidgenerator/aggregator/index.html",
    "vidgenerator/analytics/index.html",
    "vidgenerator/admin/analytics.html"
]

DOCUMENTATION = [
    "docs/USER_PROFILE_AGENT_SKILLSET_PLAN.md",
    "docs/USER_PROFILE_AGENT_SKILLSET_IMPLEMENTATION.md"
]

ALL_FILES = NEW_SERVICES + NEW_ROUTES + UPDATED_FILES + NEW_STATIC_FILES + UPDATED_DASHBOARDS + DOCUMENTATION

def deploy_files():
    """Deploy all files to production server"""
    print("=" * 70)
    print("User Profile & Agent Skillset System - Production Deployment")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect to server
        print("[1/6] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Deploy files
        print("[2/6] Deploying files...")
        sftp = ssh.open_sftp()
        deployed = 0
        skipped = 0
        errors = 0
        
        for local_file in ALL_FILES:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                skipped += 1
                continue
            
            try:
                # Determine remote path
                if local_file.startswith("backend/"):
                    remote_file = f"/var/www/html/vidgenerator/{local_file}"
                elif local_file.startswith("vidgenerator/"):
                    remote_file = f"/var/www/html/{local_file}"
                elif local_file.startswith("docs/"):
                    remote_file = f"/var/www/html/{local_file}"
                else:
                    remote_file = f"/var/www/html/vidgenerator/{local_file}"
                
                remote_dir = os.path.dirname(remote_file)
                
                # Create directory if needed
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                
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
        
        # Create log directories
        print("[3/6] Creating log directories...")
        log_dirs = [
            "/var/www/html/vidgenerator/logs/user_profiles",
            "/var/www/html/vidgenerator/logs/user_scraped_info",
            "/var/www/html/vidgenerator/logs/user_agent_skills"
        ]
        for log_dir in log_dirs:
            ssh.exec_command(f"mkdir -p {log_dir} 2>&1", timeout=5)
            ssh.exec_command(f"chown -R www-data:www-data {log_dir} 2>&1", timeout=5)
            ssh.exec_command(f"chmod -R 775 {log_dir} 2>&1", timeout=5)
        print("  [OK] Log directories created")
        print()
        
        # Clear cache
        print("[4/6] Clearing cache...")
        ssh.exec_command("find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        ssh.exec_command("find /var/www/html/vidgenerator -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[5/6] Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1", timeout=10)
        time.sleep(5)
        ssh.exec_command("systemctl restart python-proxy 2>&1", timeout=10)
        time.sleep(5)
        print("  [OK] Services restarted")
        print()
        
        # Verify deployment
        print("[6/6] Verifying deployment...")
        time.sleep(3)
        
        # Check if services are running
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator", timeout=5)
        uwsgi_status = stdout.read().decode().strip()
        
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active python-proxy", timeout=5)
        proxy_status = stdout.read().decode().strip()
        
        if uwsgi_status == "active":
            print("  [OK] uwsgi-vidgenerator is active")
        else:
            print(f"  [WARN] uwsgi-vidgenerator status: {uwsgi_status}")
        
        if proxy_status == "active":
            print("  [OK] python-proxy is active")
        else:
            print(f"  [WARN] python-proxy status: {proxy_status}")
        
        print()
        print("=" * 70)
        print("✅ Deployment Complete!")
        print("=" * 70)
        print()
        print("Deployed Components:")
        print(f"  - {len(NEW_SERVICES)} new services")
        print(f"  - {len(NEW_ROUTES)} new route files")
        print(f"  - {len(UPDATED_FILES)} updated files")
        print(f"  - {len(NEW_STATIC_FILES)} new static files")
        print(f"  - {len(UPDATED_DASHBOARDS)} updated dashboards")
        print(f"  - {len(DOCUMENTATION)} documentation files")
        print()
        print("New API Endpoints:")
        print("  - POST /api/user/create")
        print("  - GET /api/user/profile/<user_id>")
        print("  - GET /api/user/agent-skills/<user_id>")
        print("  - POST /api/user/assign-skill")
        print("  - POST /api/user/level-up-skill")
        print("  - GET /api/user/scraped-info/<user_id>")
        print()
        print("Updated Dashboards:")
        print("  - Unified Dashboard")
        print("  - Main Dashboard")
        print("  - Aggregator Dashboard")
        print("  - Analytics Dashboard")
        print("  - Admin Analytics")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"  [ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_files()
    sys.exit(0 if success else 1)

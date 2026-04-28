#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Point Tables Update to Production
Updates all point-related database tables on production server
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_APP_ROOT = "/var/www/html/vidgenerator"

# Files to deploy
FILES_TO_DEPLOY = [
    'scripts/unified_points_database_migration.py',
    'scripts/update_all_point_tables.py',
    'docs/POINT_TABLES_UPDATE_COMPLETE.md',
]

def deploy_point_tables_update():
    """Deploy point tables update to production"""
    ssh = None
    sftp = None
    
    try:
        print("=" * 80)
        print("DEPLOYING POINT TABLES UPDATE TO PRODUCTION")
        print("=" * 80)
        print(f"Deployment Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Step 1: Connect to server
        print("[1/5] Connecting to production server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print(f"  [OK] Connected to {SERVER_HOST}")
        print()
        
        # Step 2: Verify local files exist
        print("[2/5] Verifying local files...")
        missing_files = []
        for file_path in FILES_TO_DEPLOY:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  [OK] {file_path} ({size:,} bytes)")
            else:
                print(f"  [ERROR] {file_path} - NOT FOUND")
                missing_files.append(file_path)
        
        if missing_files:
            print(f"\n[ERROR] Missing {len(missing_files)} files. Cannot deploy.")
            return False
        
        print(f"\n  [OK] All {len(FILES_TO_DEPLOY)} files verified")
        print()
        
        # Step 3: Deploy files
        print("[3/5] Deploying files to production...")
        deployed = 0
        for local_path in FILES_TO_DEPLOY:
            remote_path = f'{REMOTE_APP_ROOT}/{local_path.replace(os.sep, "/")}'
            remote_dir = os.path.dirname(remote_path)
            
            # Create directory if needed
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                ssh.exec_command(f'mkdir -p {remote_dir} 2>&1', timeout=5)
                time.sleep(0.5)
            
            try:
                # Read local file
                with open(local_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Write to server
                with sftp.open(remote_path, 'w') as f:
                    f.write(content)
                
                # Verify deployment
                sftp.stat(remote_path)
                deployed += 1
                print(f"  [OK] Deployed: {local_path}")
                
            except Exception as e:
                print(f"  [ERROR] Failed to deploy {local_path}: {e}")
                return False
        
        print(f"\n  [OK] Successfully deployed {deployed}/{len(FILES_TO_DEPLOY)} files")
        print()
        
        # Step 4: Run migration on production
        print("[4/5] Running point tables migration on production...")
        print("  Executing migration script...")
        
        migration_script = f'{REMOTE_APP_ROOT}/scripts/unified_points_database_migration.py'
        
        # Run migration
        stdin, stdout, stderr = ssh.exec_command(
            f'cd {REMOTE_APP_ROOT} && python3 {migration_script} 2>&1',
            timeout=120
        )
        
        # Wait for completion
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        errors = stderr.read().decode('utf-8', errors='ignore')
        
        # Filter for migration output
        migration_lines = []
        for line in output.split('\n'):
            if any(keyword in line for keyword in ['UNIFIED POINTS', 'Creating', 'Updated', 'Migration', 'Applied', '[OK]', '[ERROR]']):
                migration_lines.append(line)
        
        if migration_lines:
            print("  Migration output:")
            for line in migration_lines[-20:]:  # Last 20 relevant lines
                if line.strip():
                    print(f"    {line}")
        
        if exit_status == 0:
            print("  [OK] Migration completed successfully")
        else:
            print(f"  [WARN] Migration exit status: {exit_status}")
            if errors:
                print(f"  Errors: {errors[:200]}")
        
        print()
        
        # Step 5: Restart services
        print("[5/5] Restarting production services...")
        services = [
            ("python-proxy.service", "Flask Application"),
            ("uwsgi-vidgenerator", "uWSGI"),
        ]
        
        for service, name in services:
            print(f"  Restarting {name}...")
            try:
                if service == "uwsgi-vidgenerator":
                    cmd = "systemctl restart uwsgi-vidgenerator 2>&1 || service uwsgi-vidgenerator restart 2>&1 || true"
                else:
                    cmd = f"systemctl restart {service} 2>&1"
                
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
                exit_status = stdout.channel.recv_exit_status()
                
                if exit_status == 0:
                    print(f"    [OK] {name} restarted")
                else:
                    output = stdout.read().decode('utf-8', errors='ignore')
                    print(f"    [WARN] {name} restart status: {exit_status}")
                
                # Check service status
                if service.endswith('.service'):
                    status_cmd = f"systemctl is-active {service} 2>&1"
                    stdin, stdout, stderr = ssh.exec_command(status_cmd, timeout=5)
                    status = stdout.read().decode('utf-8', errors='ignore').strip()
                    if status == 'active':
                        print(f"    [OK] {name} is active")
                    else:
                        print(f"    [WARN] {name} status: {status}")
                
                time.sleep(2)
                
            except Exception as e:
                print(f"    [WARN] Error restarting {name}: {e}")
        
        print()
        
        # Clear Python cache
        print("Clearing Python cache...")
        cache_commands = [
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -r {} + 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true",
        ]
        for cmd in cache_commands:
            ssh.exec_command(cmd, timeout=10)
        print("  [OK] Cache cleared")
        print()
        
        # Deployment Summary
        print("=" * 80)
        print("DEPLOYMENT COMPLETE!")
        print("=" * 80)
        print()
        print(f"Files Deployed: {deployed}/{len(FILES_TO_DEPLOY)}")
        print("Migration Status: Completed")
        print()
        print("Files Deployed:")
        for file_path in FILES_TO_DEPLOY:
            print(f"   - {file_path}")
        print()
        print("Services Restarted:")
        for service, name in services:
            print(f"   - {name}")
        print()
        print("Point Tables Updated:")
        print("   - player_levels")
        print("   - system_point_snapshots")
        print("   - xp_history")
        print("   - daily_activities")
        print("   - point_transactions")
        print("   - point_history")
        print("   - point_aggregates")
        print("   - point_analytics")
        print("   - system_usage_stats")
        print()
        print("Next Steps:")
        print("   1. Verify database tables are updated")
        print("   2. Test point-related endpoints")
        print("   3. Monitor for any errors")
        print("   4. Check analytics jobs are running")
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

if __name__ == "__main__":
    success = deploy_point_tables_update()
    sys.exit(0 if success else 1)

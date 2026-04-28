#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Profile and Battle Page Plugin Fixes to Production
Deploys the updated HTML files with all missing plugins to production server
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
    # Previously fixed pages
    'vidgenerator/profile/index.html',
    'vidgenerator/battle/index.html',
    'vidgenerator/social/index.html',
    'vidgenerator/shop/index.html',
    # Critical pages - missing both plugins
    'vidgenerator/analytics/index.html',
    'vidgenerator/quests/index.html',
    'vidgenerator/chat/index.html',
    'vidgenerator/debugger/index.html',
    'vidgenerator/trophies/index.html',
    'vidgenerator/leaderboards/index.html',
    'vidgenerator/monetization/index.html',
    'vidgenerator/battlegrounds/index.html',
    'vidgenerator/champions-league/index.html',
    'vidgenerator/editor/index.html',
    'vidgenerator/agent_support/index.html',
    'vidgenerator/beta_testing/index.html',
    # Medium priority - missing comprehensive-api-integration
    'vidgenerator/points/index.html',
    'vidgenerator/stats/index.html',
    'vidgenerator/gallery/index.html',
    'vidgenerator/generator/index.html',
    'vidgenerator/unified_dashboard/index.html',
    'vidgenerator/aggregator/index.html',
    # Documentation
    'docs/PLUGIN_LOADING_ISSUE_ANALYSIS.md'
]

def deploy_files():
    """Deploy profile, battle, social and shop page plugin fixes to production"""
    ssh = None
    sftp = None
    
    try:
        print("=" * 80)
        print("DEPLOYING PROFILE, BATTLE, SOCIAL & SHOP PAGE PLUGIN FIXES")
        print("=" * 80)
        print(f"Deployment Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Step 1: Connect to server
        print("[1/5] Connecting to production server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("  [OK] Connected to", SERVER_HOST)
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
        
        print()
        
        # Step 3: Create backups
        print("[3/5] Creating backups on server...")
        for file_path in FILES_TO_DEPLOY:
            if file_path.endswith('.html'):
                remote_path = f'{REMOTE_APP_ROOT}/{file_path.replace(os.sep, "/")}'
                backup_path = f'{remote_path}.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                
                try:
                    # Check if file exists on server
                    try:
                        sftp.stat(remote_path)
                        # File exists, create backup
                        stdin, stdout, stderr = ssh.exec_command(
                            f'cp {remote_path} {backup_path} 2>&1',
                            timeout=10
                        )
                        stdout.channel.recv_exit_status()
                        print(f"  [OK] Backup created: {os.path.basename(backup_path)}")
                    except FileNotFoundError:
                        print(f"  [INFO] File doesn't exist yet, no backup needed")
                except Exception as e:
                    print(f"  [WARN] Could not create backup: {e}")
        
        print()
        
        # Step 4: Deploy files
        print("[4/5] Deploying files to production...")
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
                print(f"       -> {remote_path}")
                
            except Exception as e:
                print(f"  [ERROR] Failed to deploy {local_path}: {e}")
                return False
        
        print(f"\n  [OK] Successfully deployed {deployed}/{len(FILES_TO_DEPLOY)} files")
        print()
        
        # Step 5: Restart services
        print("[5/5] Restarting production services...")
        services = [
            ("python-proxy.service", "Flask Application"),
            ("uwsgi-vidgenerator", "uWSGI"),
            ("nginx", "Nginx"),
        ]
        
        for service, name in services:
            print(f"  Restarting {name}...")
            try:
                if service == "uwsgi-vidgenerator":
                    cmd = "systemctl restart uwsgi-vidgenerator 2>&1 || service uwsgi-vidgenerator restart 2>&1 || true"
                elif service == "nginx":
                    cmd = "systemctl restart nginx 2>&1 || service nginx restart 2>&1 || true"
                else:
                    cmd = f"systemctl restart {service} 2>&1"
                
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
                exit_status = stdout.channel.recv_exit_status()
                
                if exit_status == 0:
                    print(f"    [OK] {name} restarted")
                else:
                    output = stdout.read().decode('utf-8', errors='ignore')
                    print(f"    [WARN] {name} restart status: {exit_status}")
                    if output:
                        print(f"           Output: {output[:100]}")
                
                # Check service status
                if service.endswith('.service'):
                    status_cmd = f"systemctl is-active {service} 2>&1"
                    stdin, stdout, stderr = ssh.exec_command(status_cmd, timeout=5)
                    status = stdout.read().decode('utf-8', errors='ignore').strip()
                    if status == 'active':
                        print(f"    [OK] {name} is active")
                    else:
                        print(f"    [WARN] {name} status: {status}")
                
                time.sleep(2)  # Small delay between restarts
                
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
        
        print("=" * 80)
        print("DEPLOYMENT COMPLETE!")
        print("=" * 80)
        print()
        print("✅ Files deployed:")
        for file_path in FILES_TO_DEPLOY:
            print(f"   - {file_path}")
        print()
        print("✅ Services restarted:")
        for service, name in services:
            print(f"   - {name}")
        print()
        print("Next Steps:")
        print("   1. Hard refresh browser: Ctrl+Shift+R (or Cmd+Shift+R on Mac)")
        print("   2. Test all fixed pages:")
        print("      - Profile, Battle, Social, Shop (previously fixed)")
        print("      - Analytics, Quests, Chat, Debugger")
        print("      - Trophies, Leaderboards, Monetization")
        print("      - Battlegrounds, Champions League, Editor")
        print("      - Agent Support, Beta Testing")
        print("      - Points, Stats, Gallery, Generator")
        print("      - Unified Dashboard, Aggregator")
        print("   3. Check browser console for any errors")
        print("   4. Verify all plugins are loading correctly")
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
    success = deploy_files()
    sys.exit(0 if success else 1)

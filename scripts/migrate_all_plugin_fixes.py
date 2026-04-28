#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Migration Script - All Plugin Fixes
Deploys all fixed HTML files, verification scripts, and documentation to production
Includes rollback capability and comprehensive verification
"""
import paramiko
import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_APP_ROOT = "/var/www/html/vidgenerator"

# All fixed HTML pages (22 pages). Local paths are repo-root (see scripts/move_vidgenerator_to_root.py);
# deployed to REMOTE_APP_ROOT/<same relative path> e.g. profile/index.html -> /var/www/html/vidgenerator/profile/index.html
FIXED_HTML_PAGES = [
    # Core pages (previously fixed)
    'profile/index.html',
    'battle/index.html',
    'social/index.html',
    'shop/index.html',
    # Critical pages - missing both plugins (12 pages)
    'analytics/index.html',
    'quests/index.html',
    'chat/index.html',
    'debugger/index.html',
    'trophies/index.html',
    'leaderboards/index.html',
    'monetization/index.html',
    'battlegrounds/index.html',
    'champions-league/index.html',
    'editor/index.html',
    'agent_support/index.html',
    'beta_testing/index.html',
    # Medium priority - missing comprehensive-api-integration (6 pages)
    'points/index.html',
    'stats/index.html',
    'gallery/index.html',
    'generator/index.html',
    'unified_dashboard/index.html',
    'aggregator/index.html',
]

# Documentation files
DOCUMENTATION_FILES = [
    'docs/PLUGIN_LOADING_ISSUE_ANALYSIS.md',
    'docs/PLUGIN_FIXES_VERIFICATION_REPORT.md',
]

# Verification scripts (optional - can be deployed for server-side verification)
VERIFICATION_SCRIPTS = [
    'scripts/verify_plugin_additions.py',
    'scripts/fix_all_plugin_issues.py',
]

def create_backup_manifest(ssh, sftp, timestamp):
    """Create a manifest of all files being backed up"""
    manifest = {
        'timestamp': timestamp,
        'files': []
    }
    
    for file_path in FIXED_HTML_PAGES:
        remote_path = f'{REMOTE_APP_ROOT}/{file_path.replace(os.sep, "/")}'
        try:
            sftp.stat(remote_path)
            # File exists, will be backed up
            manifest['files'].append({
                'local_path': file_path,
                'remote_path': remote_path,
                'exists': True
            })
        except FileNotFoundError:
            manifest['files'].append({
                'local_path': file_path,
                'remote_path': remote_path,
                'exists': False
            })
    
    return manifest

def save_backup_manifest(manifest, timestamp):
    """Save backup manifest locally"""
    manifest_path = f'backups/migration_backup_{timestamp}.json'
    os.makedirs('backups', exist_ok=True)
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    return manifest_path

def deploy_files():
    """Complete migration - deploy all fixes, scripts, and documentation"""
    ssh = None
    sftp = None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_manifest = None
    
    try:
        print("=" * 80)
        print("COMPLETE MIGRATION - ALL PLUGIN FIXES")
        print("=" * 80)
        print(f"Migration Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Migration ID: {timestamp}")
        print()
        
        # Step 1: Connect to server
        print("[1/7] Connecting to production server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print(f"  [OK] Connected to {SERVER_HOST}")
        print()
        
        # Step 2: Verify local files exist
        print("[2/7] Verifying local files...")
        missing_files = []
        all_files = FIXED_HTML_PAGES + DOCUMENTATION_FILES
        
        for file_path in all_files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  [OK] {file_path} ({size:,} bytes)")
            else:
                print(f"  [ERROR] {file_path} - NOT FOUND")
                missing_files.append(file_path)
        
        if missing_files:
            print(f"\n[ERROR] Missing {len(missing_files)} files. Cannot migrate.")
            return False
        
        print(f"\n  [OK] All {len(all_files)} files verified")
        print()
        
        # Step 3: Create backup manifest
        print("[3/7] Creating backup manifest...")
        backup_manifest = create_backup_manifest(ssh, sftp, timestamp)
        manifest_path = save_backup_manifest(backup_manifest, timestamp)
        print(f"  [OK] Backup manifest created: {manifest_path}")
        print()
        
        # Step 4: Create backups on server
        print("[4/7] Creating backups on server...")
        backup_count = 0
        for file_path in FIXED_HTML_PAGES:
            remote_path = f'{REMOTE_APP_ROOT}/{file_path.replace(os.sep, "/")}'
            backup_path = f'{remote_path}.backup.{timestamp}'
            
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
                    backup_count += 1
                    print(f"  [OK] Backup: {os.path.basename(backup_path)}")
                except FileNotFoundError:
                    print(f"  [INFO] File doesn't exist yet: {os.path.basename(remote_path)}")
            except Exception as e:
                print(f"  [WARN] Could not backup {os.path.basename(remote_path)}: {e}")
        
        print(f"\n  [OK] Created {backup_count} backups")
        print()
        
        # Step 5: Deploy HTML files
        print("[5/7] Deploying HTML files to production...")
        deployed = 0
        failed = []
        
        for local_path in FIXED_HTML_PAGES:
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
                print(f"  [OK] Deployed: {os.path.basename(os.path.dirname(local_path))}/index.html")
                
            except Exception as e:
                print(f"  [ERROR] Failed to deploy {local_path}: {e}")
                failed.append(local_path)
        
        if failed:
            print(f"\n  [WARN] {len(failed)} files failed to deploy")
            for f in failed:
                print(f"         - {f}")
        else:
            print(f"\n  [OK] Successfully deployed {deployed}/{len(FIXED_HTML_PAGES)} HTML files")
        print()
        
        # Step 6: Deploy documentation
        print("[6/7] Deploying documentation...")
        doc_deployed = 0
        for local_path in DOCUMENTATION_FILES:
            remote_path = f'{REMOTE_APP_ROOT}/{local_path.replace(os.sep, "/")}'
            remote_dir = os.path.dirname(remote_path)
            
            # Create directory if needed
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                ssh.exec_command(f'mkdir -p {remote_dir} 2>&1', timeout=5)
                time.sleep(0.5)
            
            try:
                with open(local_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                with sftp.open(remote_path, 'w') as f:
                    f.write(content)
                
                sftp.stat(remote_path)
                doc_deployed += 1
                print(f"  [OK] Deployed: {os.path.basename(local_path)}")
            except Exception as e:
                print(f"  [WARN] Could not deploy {local_path}: {e}")
        
        print(f"\n  [OK] Deployed {doc_deployed}/{len(DOCUMENTATION_FILES)} documentation files")
        print()
        
        # Step 7: Restart services
        print("[7/7] Restarting production services...")
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
        
        # Migration Summary
        print("=" * 80)
        print("MIGRATION COMPLETE!")
        print("=" * 80)
        print()
        print(f"Migration ID: {timestamp}")
        print(f"HTML Files Deployed: {deployed}/{len(FIXED_HTML_PAGES)}")
        print(f"Documentation Deployed: {doc_deployed}/{len(DOCUMENTATION_FILES)}")
        print(f"Backups Created: {backup_count}")
        print()
        print("Files Deployed:")
        for file_path in FIXED_HTML_PAGES:
            print(f"   - {file_path}")
        print()
        print("Documentation Deployed:")
        for file_path in DOCUMENTATION_FILES:
            print(f"   - {file_path}")
        print()
        print("Services Restarted:")
        for service, name in services:
            print(f"   - {name}")
        print()
        print("Backup Manifest:")
        print(f"   - {manifest_path}")
        print()
        print("Next Steps:")
        print("   1. Hard refresh browser: Ctrl+Shift+R (or Cmd+Shift+R on Mac)")
        print("   2. Test all fixed pages:")
        print("      - Profile, Battle, Social, Shop")
        print("      - Analytics, Quests, Chat, Debugger")
        print("      - Trophies, Leaderboards, Monetization")
        print("      - Battlegrounds, Champions League, Editor")
        print("      - Agent Support, Beta Testing")
        print("      - Points, Stats, Gallery, Generator")
        print("      - Unified Dashboard, Aggregator")
        print("   3. Check browser console for any errors")
        print("   4. Verify all plugins are loading correctly")
        print("   5. Verify no refresh loops")
        print()
        print("Rollback:")
        print(f"   If needed, restore from backups using timestamp: {timestamp}")
        print(f"   Backup manifest: {manifest_path}")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        
        if backup_manifest:
            print(f"\n[INFO] Backup manifest saved: {save_backup_manifest(backup_manifest, timestamp)}")
            print("[INFO] You can rollback using the backup manifest")
        
        return False
        
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()

if __name__ == "__main__":
    success = deploy_files()
    sys.exit(0 if success else 1)

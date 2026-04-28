#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rollback Migration Script
Restores files from backup using migration backup manifest
"""
import paramiko
import os
import sys
import json
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_APP_ROOT = "/var/www/html/vidgenerator"

def rollback_from_manifest(manifest_path):
    """Rollback using backup manifest"""
    ssh = None
    sftp = None
    
    try:
        # Load manifest
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        timestamp = manifest.get('timestamp', 'unknown')
        
        print("=" * 80)
        print("ROLLBACK MIGRATION")
        print("=" * 80)
        print(f"Backup Timestamp: {timestamp}")
        print(f"Manifest: {manifest_path}")
        print()
        
        # Confirm rollback
        print("WARNING: This will restore files from backup!")
        print("Press Ctrl+C to cancel, or Enter to continue...")
        try:
            input()
        except KeyboardInterrupt:
            print("\nRollback cancelled.")
            return False
        
        # Connect to server
        print("[1/3] Connecting to production server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print(f"  [OK] Connected to {SERVER_HOST}")
        print()
        
        # Restore files
        print("[2/3] Restoring files from backup...")
        restored = 0
        failed = []
        
        for file_info in manifest.get('files', []):
            if not file_info.get('exists', False):
                continue
            
            remote_path = file_info['remote_path']
            backup_path = f"{remote_path}.backup.{timestamp}"
            
            try:
                # Check if backup exists
                sftp.stat(backup_path)
                
                # Restore from backup
                stdin, stdout, stderr = ssh.exec_command(
                    f'cp {backup_path} {remote_path} 2>&1',
                    timeout=10
                )
                exit_status = stdout.channel.recv_exit_status()
                
                if exit_status == 0:
                    restored += 1
                    print(f"  [OK] Restored: {os.path.basename(remote_path)}")
                else:
                    error = stdout.read().decode('utf-8', errors='ignore')
                    print(f"  [ERROR] Failed to restore {os.path.basename(remote_path)}: {error}")
                    failed.append(remote_path)
                    
            except FileNotFoundError:
                print(f"  [WARN] Backup not found: {os.path.basename(backup_path)}")
                failed.append(remote_path)
            except Exception as e:
                print(f"  [ERROR] Error restoring {os.path.basename(remote_path)}: {e}")
                failed.append(remote_path)
        
        print(f"\n  [OK] Restored {restored} files")
        if failed:
            print(f"  [WARN] {len(failed)} files could not be restored")
        print()
        
        # Restart services
        print("[3/3] Restarting production services...")
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
                    print(f"    [WARN] {name} restart status: {exit_status}")
                
                time.sleep(2)
                
            except Exception as e:
                print(f"    [WARN] Error restarting {name}: {e}")
        
        print()
        print("=" * 80)
        print("ROLLBACK COMPLETE!")
        print("=" * 80)
        print(f"Files Restored: {restored}")
        if failed:
            print(f"Files Failed: {len(failed)}")
        print()
        
        return True
        
    except FileNotFoundError:
        print(f"[ERROR] Manifest file not found: {manifest_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid manifest file: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Rollback failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python rollback_migration.py <manifest_path>")
        print("Example: python rollback_migration.py backups/migration_backup_20260125_204903.json")
        sys.exit(1)
    
    manifest_path = sys.argv[1]
    success = rollback_from_manifest(manifest_path)
    sys.exit(0 if success else 1)

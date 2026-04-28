#!/usr/bin/env python3
"""
Deploy Migration to Production
Runs the migration script on production server
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

FILES_TO_DEPLOY = [
    "scripts/migrate_all_missing_tables.py",
    "scripts/check_and_fix_functions_tables.py"
]

def deploy_and_run_migration():
    """Deploy migration script and run it on production"""
    print("=" * 70)
    print("DEPLOY MIGRATION TO PRODUCTION")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect to server
        print("[1/3] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Deploy files
        print("[2/3] Deploying migration scripts...")
        sftp = ssh.open_sftp()
        deployed = 0
        
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                continue
            
            try:
                remote_file = f"/var/www/html/vidgenerator/{local_file}"
                remote_dir = os.path.dirname(remote_file)
                
                # Create remote directory
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                
                # Copy file
                sftp.put(local_file, remote_file)
                print(f"  [OK] Deployed {local_file}")
                deployed += 1
                
            except Exception as e:
                print(f"  [ERROR] Failed to deploy {local_file}: {e}")
        
        sftp.close()
        print(f"  [SUMMARY] Deployed {deployed}/{len(FILES_TO_DEPLOY)} files")
        print()
        
        # Run migration
        print("[3/3] Running migration on production...")
        remote_script = "/var/www/html/vidgenerator/scripts/migrate_all_missing_tables.py"
        
        stdin, stdout, stderr = ssh.exec_command(f"cd /var/www/html/vidgenerator && python3 {remote_script} 2>&1", timeout=60)
        
        output = stdout.read().decode()
        errors = stderr.read().decode()
        
        if "MIGRATION COMPLETE" in output or "All tables created successfully" in output:
            print("  [OK] Migration completed successfully")
            print()
            print("Migration output:")
            # Show last 20 lines
            lines = output.split('\n')
            for line in lines[-20:]:
                if line.strip():
                    print(f"    {line}")
        else:
            print("  [WARN] Migration may have issues")
            print("Output:", output[:500])
            if errors:
                print("Errors:", errors[:500])
        
        ssh.close()
        
        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Verify tables: Run check script on production")
        print("  2. Populate data: Run data population scripts if needed")
        print()
        
    except Exception as e:
        print(f"\n  [ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    deploy_and_run_migration()

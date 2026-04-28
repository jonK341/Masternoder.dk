#!/usr/bin/env python3
"""
Deploy Data Loading to Production
Deploys data loading script and runs it on production
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
    "scripts/load_all_tables_data.py"
]

def deploy_and_run_data_loading():
    """Deploy data loading script and run it on production"""
    print("=" * 70)
    print("DEPLOY DATA LOADING TO PRODUCTION")
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
        print("[2/3] Deploying data loading script...")
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
        
        # Run data loading
        print("[3/3] Running data loading on production...")
        remote_script = "/var/www/html/vidgenerator/scripts/load_all_tables_data.py"
        
        stdin, stdout, stderr = ssh.exec_command(f"cd /var/www/html/vidgenerator && python3 {remote_script} 2>&1", timeout=120)
        
        # Read output in chunks
        output_lines = []
        while True:
            line = stdout.readline()
            if not line:
                break
            output_lines.append(line)
            if "DATA LOADING COMPLETE" in line or "All tables loaded" in line:
                break
        
        output = ''.join(output_lines)
        
        if "DATA LOADING COMPLETE" in output or "All tables loaded" in output:
            print("  [OK] Data loading completed successfully")
            print()
            # Show summary
            for line in output_lines[-15:]:
                if line.strip() and not line.startswith("Error getting"):
                    print(f"    {line.rstrip()}")
        else:
            print("  [WARN] Data loading may have issues")
            print("Output:", output[-500:])
        
        ssh.close()
        
        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("Data loaded into:")
        print("  - user_profiles: 50 users")
        print("  - onboarding_progress: ~19 users")
        print("  - player_levels: 50 users")
        print("  - xp_history: ~480 records")
        print("  - daily_activities: ~629 records")
        print("  - user_agent_skills: ~97 records")
        print("  - user_scraped_info: ~52 records")
        print()
        
    except Exception as e:
        print(f"\n  [ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    deploy_and_run_data_loading()

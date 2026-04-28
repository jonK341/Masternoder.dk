#!/usr/bin/env python3
"""
Deploy improved placeholder video generation to production server
"""
import os
import sys
import paramiko
from scp import SCPClient

# Fix UnicodeEncodeError on Windows
sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

# Files to deploy
FILES_TO_DEPLOY = [
    ("src/services/documentary_pipeline/pipeline_orchestrator.py", f"{REMOTE_PATH}/src/services/documentary_pipeline/pipeline_orchestrator.py"),
]

def deploy():
    """Deploy improved placeholder video generation"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("DEPLOYING IMPROVED PLACEHOLDER VIDEO GENERATION")
        print("=" * 80)
        print(f"Server: {SERVER_HOST}")
        print(f"Target: {REMOTE_PATH}")
        print()
        
        print("Connecting to server...")
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        print("[OK] Connected!")
        print()
        
        scp = SCPClient(ssh_client.get_transport())
        deployed_count = 0
        
        print("Deploying files...")
        print("-" * 80)
        
        for local_path, remote_path in FILES_TO_DEPLOY:
            if not os.path.exists(local_path):
                print(f"[SKIP] {local_path} - File not found")
                continue
            
            try:
                scp.put(local_path, remote_path)
                file_size = os.path.getsize(local_path)
                print(f"[OK] {local_path} -> {remote_path} ({file_size:,} bytes)")
                deployed_count += 1
            except Exception as e:
                print(f"[ERROR] Failed to deploy {local_path}: {e}")
        
        scp.close()
        
        print()
        print("=" * 80)
        print(f"Deployment Summary: {deployed_count} file(s) deployed")
        print("=" * 80)
        print()
        
        print("Restarting services...")
        print("-" * 80)
        
        stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code == 0:
            print("[OK] systemctl restart uwsgi")
        else:
            print(f"[WARN] systemctl restart uwsgi - Exit code: {exit_code}")
        
        stdin, stdout, stderr = ssh_client.exec_command("systemctl restart python-proxy.service")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code == 0:
            print("[OK] systemctl restart python-proxy.service")
        else:
            print(f"[WARN] systemctl restart python-proxy.service - Exit code: {exit_code}")
        
        print()
        print("=" * 80)
        print("[OK] DEPLOYMENT COMPLETE")
        print("=" * 80)
        print()
        print("✅ Improved placeholder videos deployed!")
        print("   - Videos now show gradient background instead of black")
        print("   - Text overlay shows prompt/description")
        print()
        print("⚠️  NOTE: For real video generation, configure API keys:")
        print("   - RUNWAYML_API_KEY")
        print("   - PIKA_LABS_API_KEY")
        print("   - STABILITY_AI_API_KEY")
        print()
        print("See GENERATOR_API_SETUP.md for details.")
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        ssh_client.close()

if __name__ == '__main__':
    deploy()


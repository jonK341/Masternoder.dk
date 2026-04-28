#!/usr/bin/env python3
"""
Deploy AI Video Content Fix - Real Content Generation
"""
import os
import sys
import paramiko
from scp import SCPClient

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
scp = None

try:
    print("=" * 80)
    print("DEPLOYING AI VIDEO CONTENT FIX - REAL CONTENT GENERATION")
    print("=" * 80)
    
    ssh_client.connect(hostname=SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    scp = SCPClient(ssh_client.get_transport())
    
    files_to_deploy = [
        ('src/services/documentary_pipeline/pipeline_orchestrator.py', f'{REMOTE_PATH}/src/services/documentary_pipeline/pipeline_orchestrator.py'),
    ]
    
    for local_path, remote_path in files_to_deploy:
        print(f"\n1. Deploying {local_path}...")
        scp.put(local_path, remote_path)
        print(f"   [OK] Deployed to {remote_path}")
    
    print("\n2. Setting file permissions...")
    for _, remote_path in files_to_deploy:
        stdin, stdout, stderr = ssh_client.exec_command(f"chmod 644 {remote_path} && chown www-data:www-data {remote_path} 2>&1")
        output = stdout.read().decode('utf-8', errors='ignore')
        if output.strip():
            print(f"   {output}")
    
    print("\n3. Restarting uWSGI service...")
    stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi 2>&1")
    restart_output = stdout.read().decode('utf-8', errors='ignore')
    if restart_output.strip():
        print(f"   {restart_output}")
    else:
        print("   [OK] Service restarted")
    
    print("\n" + "=" * 80)
    print("✅ AI VIDEO CONTENT FIX DEPLOYED!")
    print("=" * 80)
    print("\nImprovements:")
    print("  ✅ Fixed image extraction from gathered media")
    print("  ✅ Image rotation across clips for variety")
    print("  ✅ AI provider rotation (RunwayML, Pika, Stable Video)")
    print("  ✅ Image-to-video generation using gathered images")
    print("  ✅ Enhanced placeholder creation with image-based clips")
    print("  ✅ Better error handling and logging")
    print("  ✅ Audio integration in final compilation")
    print("  ✅ Proper fallback chain for video generation")
    print("\nThe system will now:")
    print("  1. Use gathered images for image-to-video generation")
    print("  2. Rotate AI providers for each clip")
    print("  3. Create image-based clips when API keys unavailable")
    print("  4. Add gathered audio to final MP4 compilation")
    print("  5. Generate real content instead of black screens")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
finally:
    if scp:
        scp.close()
    ssh_client.close()


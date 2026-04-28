#!/usr/bin/env python3
"""
Deploy Enhanced Chat Page with API Integration
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
    print("DEPLOYING ENHANCED CHAT PAGE & API")
    print("=" * 80)
    
    ssh_client.connect(hostname=SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    scp = SCPClient(ssh_client.get_transport())
    
    files_to_deploy = [
        ('vidgenerator/chat/index.html', f'{REMOTE_PATH}/vidgenerator/chat/index.html'),
        ('backend/routes/chat_enhanced.py', f'{REMOTE_PATH}/backend/routes/chat_enhanced.py'),
    ]
    
    # Create directories first
    print("\n0. Creating directories...")
    stdin, stdout, stderr = ssh_client.exec_command(f"mkdir -p {REMOTE_PATH}/vidgenerator/chat 2>&1")
    output = stdout.read().decode('utf-8', errors='ignore')
    if output.strip():
        print(f"   {output}")
    
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
    print("✅ ENHANCED CHAT DEPLOYED!")
    print("=" * 80)
    print("\nChat Enhancements:")
    print("  ✅ Updated navigation links with all pages")
    print("  ✅ API integration for sending messages")
    print("  ✅ Chat history loading")
    print("  ✅ Real-time message polling (every 3 seconds)")
    print("  ✅ Online users tracking")
    print("  ✅ Chat points integration")
    print("  ✅ Better error handling")
    print("  ✅ Toast notifications for user feedback")
    print("\nNew API Endpoints:")
    print("  ✅ POST /api/chat/send - Send chat message")
    print("  ✅ GET /api/chat/history - Get chat history")
    print("  ✅ GET /api/chat/messages - Get new messages since timestamp")
    print("  ✅ GET /api/chat/users - Get online users")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
finally:
    if scp:
        scp.close()
    ssh_client.close()


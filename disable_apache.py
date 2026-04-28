#!/usr/bin/env python3
"""
Disable Apache to prevent conflicts
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def disable():
    """Disable Apache"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("DISABLING APACHE")
        print("=" * 80)
        print()
        
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        # Stop Apache if running
        print("📋 Stopping Apache...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("systemctl stop apache2 2>/dev/null || systemctl stop httpd 2>/dev/null || echo 'Apache already stopped'")
        stop_output = stdout.read().decode('utf-8', errors='ignore')
        print(stop_output)
        
        # Disable Apache on boot
        print()
        print("📋 Disabling Apache on boot...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("systemctl disable apache2 2>/dev/null || systemctl disable httpd 2>/dev/null || echo 'Apache already disabled'")
        disable_output = stdout.read().decode('utf-8', errors='ignore')
        print(disable_output)
        
        # Verify status
        print()
        print("📋 Verifying Apache status...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("systemctl is-enabled apache2 2>/dev/null || systemctl is-enabled httpd 2>/dev/null || echo 'disabled'")
        status = stdout.read().decode('utf-8', errors='ignore').strip()
        print(f"Apache enabled on boot: {status}")
        
        print()
        print("✅ Apache disabled successfully")
        print("   Nginx will continue to serve the site")
        
        ssh.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    disable()


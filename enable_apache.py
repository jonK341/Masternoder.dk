#!/usr/bin/env python3
"""
Enable Apache and configure it
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def enable():
    """Enable Apache"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("ENABLING APACHE")
        print("=" * 80)
        print()
        
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        # Stop Nginx first (since it's using port 80)
        print("📋 Stopping Nginx (to free port 80)...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("systemctl stop nginx")
        stop_output = stdout.read().decode('utf-8', errors='ignore')
        print("Nginx stopped")
        
        # Enable Apache site
        print()
        print("📋 Enabling Apache site...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("a2ensite masternoder.dk.conf 2>&1")
        enable_output = stdout.read().decode('utf-8', errors='ignore')
        print(enable_output)
        
        # Enable required Apache modules
        print()
        print("📋 Enabling Apache proxy modules...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("a2enmod proxy proxy_http rewrite 2>&1")
        modules_output = stdout.read().decode('utf-8', errors='ignore')
        print(modules_output)
        
        # Test Apache configuration
        print()
        print("📋 Testing Apache configuration...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("apache2ctl configtest 2>&1 || httpd -t 2>&1")
        config_test = stdout.read().decode('utf-8', errors='ignore')
        print(config_test)
        
        # Enable Apache on boot
        print()
        print("📋 Enabling Apache on boot...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("systemctl enable apache2 2>/dev/null || systemctl enable httpd 2>/dev/null")
        enable_boot = stdout.read().decode('utf-8', errors='ignore')
        print("Apache enabled on boot")
        
        # Start Apache
        print()
        print("📋 Starting Apache...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("systemctl start apache2 2>/dev/null || systemctl start httpd 2>/dev/null")
        start_output = stdout.read().decode('utf-8', errors='ignore')
        if start_output:
            print(start_output)
        
        # Check Apache status
        print()
        print("📋 Checking Apache status...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("systemctl status apache2 --no-pager | head -15 2>/dev/null || systemctl status httpd --no-pager | head -15 2>/dev/null")
        status = stdout.read().decode('utf-8', errors='ignore')
        print(status)
        
        # Check if Apache is listening
        print()
        print("📋 Checking if Apache is listening on port 80...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("netstat -tlnp 2>/dev/null | grep ':80' | grep -E 'apache|httpd' || ss -tlnp 2>/dev/null | grep ':80' | grep -E 'apache|httpd' || echo 'Not listening on port 80'")
        listening = stdout.read().decode('utf-8', errors='ignore')
        print(listening)
        
        print()
        print("=" * 80)
        if "active (running)" in status.lower():
            print("✅ Apache enabled and running!")
        else:
            print("⚠️  Apache may not be running. Check status above.")
        print("=" * 80)
        
        ssh.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    enable()


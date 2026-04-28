#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update Nginx to Not Cache HTML Files
Adds no-cache headers for HTML files
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def update_nginx():
    """Update nginx config to not cache HTML"""
    ssh = None
    try:
        print("Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Backup nginx config
        print("Backing up nginx config...")
        ssh.exec_command("cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup.$(date +%Y%m%d_%H%M%S) 2>&1", timeout=10)
        print("  [OK] Backup created")
        print()
        
        # Read current config
        print("Reading nginx config...")
        stdin, stdout, stderr = ssh.exec_command("cat /etc/nginx/sites-available/default", timeout=10)
        config = stdout.read().decode('utf-8', errors='ignore')
        
        # Check if HTML no-cache already exists
        if 'location ~ \\.html$' in config:
            print("  [INFO] HTML no-cache rule already exists")
            return
        
        # Add HTML no-cache rule before the main location block
        html_no_cache = '''
    # Don't cache HTML files
    location ~ \\.html$ {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }
'''
        
        # Insert before the main /vidgenerator/ location block
        if 'location /vidgenerator/ {' in config:
            config = config.replace('    location /vidgenerator/ {', html_no_cache + '    location /vidgenerator/ {')
        else:
            # Append to server block
            config = config.replace('    server_name', html_no_cache + '    server_name')
        
        # Write updated config
        print("Writing updated nginx config...")
        sftp = ssh.open_sftp()
        with sftp.open('/etc/nginx/sites-available/default', 'w') as f:
            f.write(config)
        sftp.close()
        print("  [OK] Config updated")
        print()
        
        # Test nginx config
        print("Testing nginx config...")
        stdin, stdout, stderr = ssh.exec_command("nginx -t 2>&1", timeout=10)
        output = stdout.read().decode('utf-8', errors='ignore')
        if 'syntax is ok' in output.lower():
            print("  [OK] Config is valid")
        else:
            print(f"  [ERROR] Config test failed: {output}")
            return
        
        # Reload nginx
        print("Reloading nginx...")
        ssh.exec_command("systemctl reload nginx 2>&1", timeout=10)
        print("  [OK] Nginx reloaded")
        print()
        
        print("=" * 70)
        print("NGINX UPDATED")
        print("=" * 70)
        print("HTML files will now be served with no-cache headers")
        
    except Exception as e:
        print(f"\n[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh:
            ssh.close()

if __name__ == '__main__':
    update_nginx()

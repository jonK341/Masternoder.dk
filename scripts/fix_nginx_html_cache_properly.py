#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Nginx HTML Cache Properly
Adds proper no-cache rule for HTML files
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_nginx():
    """Fix nginx config"""
    ssh = None
    try:
        print("Connecting...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        # Read config
        stdin, stdout, stderr = ssh.exec_command("cat /etc/nginx/sites-available/default", timeout=10)
        config = stdout.read().decode('utf-8', errors='ignore')
        
        # Check if rule exists
        if 'location ~ \\.html$' in config or 'location ~* \\.html$' in config:
            print("HTML no-cache rule already exists")
            # Verify it's correct
            if 'no-cache' in config or 'no-store' in config:
                print("Rule looks correct")
                return
        
        # Add rule - find server block and add before main location
        lines = config.split('\n')
        new_lines = []
        added = False
        
        for i, line in enumerate(lines):
            # Add before first location block in server context
            if not added and 'location /vidgenerator/static' in line:
                # Add HTML no-cache rule before static files
                new_lines.append('    # Don\'t cache HTML files')
                new_lines.append('    location ~ \\.html$ {')
                new_lines.append('        add_header Cache-Control "no-cache, no-store, must-revalidate";')
                new_lines.append('        add_header Pragma "no-cache";')
                new_lines.append('        add_header Expires "0";')
                new_lines.append('        proxy_pass http://127.0.0.1:5000;')
                new_lines.append('        proxy_set_header Host $host;')
                new_lines.append('        proxy_set_header X-Real-IP $remote_addr;')
                new_lines.append('    }')
                new_lines.append('')
                added = True
            new_lines.append(line)
        
        if not added:
            # Try adding after server_name
            new_lines = []
            added = False
            for i, line in enumerate(lines):
                if not added and 'server_name' in line:
                    new_lines.append(line)
                    new_lines.append('')
                    new_lines.append('    # Don\'t cache HTML files')
                    new_lines.append('    location ~ \\.html$ {')
                    new_lines.append('        add_header Cache-Control "no-cache, no-store, must-revalidate";')
                    new_lines.append('        add_header Pragma "no-cache";')
                    new_lines.append('        add_header Expires "0";')
                    new_lines.append('        proxy_pass http://127.0.0.1:5000;')
                    new_lines.append('        proxy_set_header Host $host;')
                    new_lines.append('        proxy_set_header X-Real-IP $remote_addr;')
                    new_lines.append('    }')
                    new_lines.append('')
                    added = True
                else:
                    new_lines.append(line)
        
        if added:
            config = '\n'.join(new_lines)
            
            # Write config
            sftp = ssh.open_sftp()
            with sftp.open('/etc/nginx/sites-available/default', 'w') as f:
                f.write(config)
            sftp.close()
            
            # Test
            stdin, stdout, stderr = ssh.exec_command("nginx -t 2>&1", timeout=10)
            output = stdout.read().decode('utf-8', errors='ignore')
            if 'syntax is ok' in output.lower():
                print("Config valid, reloading...")
                ssh.exec_command("systemctl reload nginx 2>&1", timeout=10)
                print("Done!")
            else:
                print(f"Config error: {output}")
        else:
            print("Could not find insertion point")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh:
            ssh.close()

if __name__ == '__main__':
    fix_nginx()

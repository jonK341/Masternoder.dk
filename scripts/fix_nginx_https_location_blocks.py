#!/usr/bin/env python3
"""
Fix Nginx HTTPS Location Blocks
Adds location blocks to HTTPS server block
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_nginx():
    """Fix nginx HTTPS location blocks"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        nginx_config = "/etc/nginx/sites-enabled/masternoder.dk"
        
        # Create backup
        print("[1/5] Creating backup...")
        stdin, stdout, stderr = ssh.exec_command(
            f"cp {nginx_config} {nginx_config}.backup.$(date +%Y%m%d_%H%M%S)",
            timeout=10
        )
        stdout.read()
        print("  [OK] Backup created")
        
        # Read the current config
        print()
        print("[2/5] Reading current config...")
        sftp = ssh.open_sftp()
        with sftp.open(nginx_config, 'r') as f:
            config_content = f.read().decode('utf-8')
        sftp.close()
        print(f"  [OK] Read {len(config_content)} bytes")
        
        # Find the HTTPS server block and add location blocks
        print()
        print("[3/5] Adding location blocks to HTTPS server block...")
        
        # Find where to insert (after "ssl_dhparam" line in HTTPS server block)
        lines = config_content.split('\n')
        insert_line = None
        for i, line in enumerate(lines):
            if 'ssl_dhparam' in line and 'listen 443' in '\n'.join(lines[max(0, i-10):i]):
                # Found the HTTPS server block, find the closing brace or next server block
                for j in range(i+1, min(i+20, len(lines))):
                    if lines[j].strip() == '}' or lines[j].strip().startswith('server {'):
                        insert_line = j
                        break
                break
        
        if insert_line is None:
            print("  [ERROR] Could not find insertion point")
            return False
        
        # Get the location blocks from HTTP server block (lines 6-62)
        location_blocks = []
        for i in range(5, 62):  # Lines 6-62 (0-indexed: 5-61)
            if i < len(lines):
                location_blocks.append(lines[i])
        
        # Insert location blocks before the closing brace
        new_lines = lines[:insert_line] + location_blocks + lines[insert_line:]
        new_config = '\n'.join(new_lines)
        
        # Write the new config
        print()
        print("[4/5] Writing new config...")
        sftp = ssh.open_sftp()
        with sftp.open(nginx_config, 'w') as f:
            f.write(new_config.encode('utf-8'))
        sftp.close()
        print("  [OK] Config written")
        
        # Test nginx config
        print()
        print("[5/5] Testing nginx configuration...")
        stdin, stdout, stderr = ssh.exec_command("nginx -t 2>&1", timeout=10)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if "syntax is ok" in output or "syntax is ok" in error:
            print("  [OK] Nginx config is valid")
            
            # Reload nginx
            print()
            print("Reloading nginx...")
            stdin2, stdout2, stderr2 = ssh.exec_command("systemctl reload nginx", timeout=10)
            stdout2.read()
            print("  [OK] Nginx reloaded")
        else:
            print(f"  [ERROR] Nginx config test failed:")
            print(f"    {output}")
            print(f"    {error}")
            # Restore backup
            print()
            print("Restoring backup...")
            stdin3, stdout3, stderr3 = ssh.exec_command(
                f"cp {nginx_config}.backup.* {nginx_config}",
                timeout=10
            )
            return False
        
        print()
        print("="*70)
        print("NGINX HTTPS LOCATION BLOCKS FIXED")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_nginx()

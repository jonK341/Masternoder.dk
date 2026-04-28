#!/usr/bin/env python3
"""
Fix Nginx HTTPS Properly
Properly adds location blocks to HTTPS server block
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_nginx():
    """Fix nginx HTTPS properly"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        nginx_config = "/etc/nginx/sites-enabled/masternoder.dk"
        
        # Create backup
        print("[1/6] Creating backup...")
        stdin, stdout, stderr = ssh.exec_command(
            f"cp {nginx_config} {nginx_config}.backup.$(date +%Y%m%d_%H%M%S)",
            timeout=10
        )
        stdout.read()
        print("  [OK] Backup created")
        
        # Read the file
        print()
        print("[2/6] Reading config...")
        sftp = ssh.open_sftp()
        with sftp.open(nginx_config, 'r') as f:
            lines = f.read().decode('utf-8').split('\n')
        sftp.close()
        print(f"  [OK] Read {len(lines)} lines")
        
        # Find HTTPS server block
        print()
        print("[3/6] Finding HTTPS server block...")
        https_start = None
        https_end = None
        
        for i, line in enumerate(lines):
            if 'listen 443' in line and 'ssl' in line and not line.strip().startswith('#'):
                https_start = i
                # Find the closing brace
                brace_count = 0
                for j in range(i, len(lines)):
                    brace_count += lines[j].count('{')
                    brace_count -= lines[j].count('}')
                    if brace_count == 0 and j > i:
                        https_end = j
                        break
                break
        
        if https_start is None or https_end is None:
            print("  [ERROR] Could not find HTTPS server block")
            return False
        
        print(f"  [OK] HTTPS server block: lines {https_start+1}-{https_end+1}")
        
        # Get location blocks from HTTP server (lines 6-62, 0-indexed: 5-61)
        print()
        print("[4/6] Extracting location blocks from HTTP server block...")
        location_blocks = []
        for i in range(5, 62):
            if i < len(lines):
                location_blocks.append(lines[i])
        
        print(f"  [OK] Extracted {len(location_blocks)} lines")
        
        # Insert location blocks before the closing brace of HTTPS server block
        print()
        print("[5/6] Inserting location blocks into HTTPS server block...")
        new_lines = lines[:https_end] + location_blocks + lines[https_end:]
        new_config = '\n'.join(new_lines)
        
        # Write the new config
        print()
        print("[6/6] Writing new config...")
        sftp = ssh.open_sftp()
        with sftp.open(nginx_config, 'w') as f:
            f.write(new_config.encode('utf-8'))
        sftp.close()
        print("  [OK] Config written")
        
        # Test nginx config
        print()
        print("Testing nginx configuration...")
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
            return False
        
        print()
        print("="*70)
        print("NGINX HTTPS LOCATION BLOCKS ADDED SUCCESSFULLY")
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

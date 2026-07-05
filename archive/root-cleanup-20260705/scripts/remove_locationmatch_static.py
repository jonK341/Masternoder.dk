"""
Remove or move LocationMatch to properly exclude static files
"""
import paramiko
import os
import sys
import time

# Configure UTF-8 for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv('DEPLOY_HOST', 'masternoder.dk')
USERNAME = os.getenv('DEPLOY_USER', 'root')
PASSWORD = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

print("=" * 80)
print("REMOVING/MOVING LocationMatch TO FIX STATIC FILES")
print("=" * 80)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {SERVER_HOST}...")
    ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    print("[OK] Connected!")
    print()

    config_path = "/etc/apache2/sites-available/000-default.conf"
    
    # Read HTTP config
    print("[1] Reading HTTP configuration...")
    stdin, stdout, stderr = ssh.exec_command(f"cat {config_path}")
    http_content = stdout.read().decode('utf-8', errors='ignore')
    
    print("Current config structure:")
    # Find LocationMatch
    if 'LocationMatch' in http_content:
        lines = http_content.split('\n')
        in_locationmatch = False
        for i, line in enumerate(lines):
            if 'LocationMatch' in line:
                in_locationmatch = True
                print(f"  Line {i+1}: {line.strip()}")
            elif in_locationmatch:
                print(f"  Line {i+1}: {line.strip()}")
                if '</LocationMatch>' in line:
                    in_locationmatch = False
                    break
    print()
    
    # Create backup
    stdin, stdout, stderr = ssh.exec_command(f"cp {config_path} {config_path}.backup.$(date +%Y%m%d_%H%M%S)")
    print("[OK] Backup created")
    
    # Strategy: Move LocationMatch INSIDE VirtualHost, AFTER static file configuration
    # This ensures static files are handled first
    
    # Find VirtualHost section
    vhost_start = http_content.find('<VirtualHost')
    vhost_end = http_content.find('</VirtualHost>')
    
    if vhost_start != -1 and vhost_end != -1:
        # Extract LocationMatch block
        locationmatch_start = http_content.find('<LocationMatch')
        locationmatch_end = http_content.find('</LocationMatch>')
        
        if locationmatch_start != -1 and locationmatch_end != -1:
            locationmatch_block = http_content[locationmatch_start:locationmatch_end + len('</LocationMatch>')]
            
            # Remove LocationMatch from outside VirtualHost
            http_without_locationmatch = http_content[:locationmatch_start] + http_content[locationmatch_end + len('</LocationMatch>'):]
            
            # Find where to insert it (after static file Directory block, before ProxyPass)
            # Find Directory block end
            dir_end = http_without_locationmatch.find('</Directory>', vhost_start)
            if dir_end != -1:
                # Find next non-empty line after Directory
                insert_pos = http_without_locationmatch.find('\n', dir_end) + 1
                # Skip empty lines
                while insert_pos < len(http_without_locationmatch) and http_without_locationmatch[insert_pos:insert_pos+1].isspace():
                    insert_pos += 1
                
                # Update LocationMatch to exclude static
                updated_locationmatch = locationmatch_block.replace(
                    'LocationMatch "^/vidgenerator',
                    'LocationMatch "^/vidgenerator(?!.*/static)'
                )
                
                # Insert after Directory, before ProxyPass
                new_http = http_without_locationmatch[:insert_pos] + '    ' + updated_locationmatch + '\n\n' + http_without_locationmatch[insert_pos:]
            else:
                # Fallback: insert before ProxyPass
                proxypass_pos = http_without_locationmatch.find('ProxyPass /vidgenerator', vhost_start)
                if proxypass_pos != -1:
                    updated_locationmatch = locationmatch_block.replace(
                        'LocationMatch "^/vidgenerator',
                        'LocationMatch "^/vidgenerator(?!.*/static)'
                    )
                    new_http = http_without_locationmatch[:proxypass_pos] + '    ' + updated_locationmatch + '\n\n    ' + http_without_locationmatch[proxypass_pos:]
                else:
                    new_http = http_without_locationmatch
        else:
            print("[INFO] LocationMatch block not found or already moved")
            new_http = http_content
    else:
        print("[ERROR] VirtualHost section not found")
        new_http = http_content
    
    # Write HTTP config
    print("[2] Writing updated HTTP configuration...")
    sftp = ssh.open_sftp()
    try:
        temp_file = f"{config_path}.new"
        with sftp.file(temp_file, 'w') as f:
            f.write(new_http)
        
        stdin, stdout, stderr = ssh.exec_command(f"mv {temp_file} {config_path}")
        print("[OK] HTTP configuration updated")
    finally:
        sftp.close()
    
    # Test Apache configuration
    print("[3] Testing Apache configuration...")
    stdin, stdout, stderr = ssh.exec_command("apache2ctl configtest 2>&1")
    test_result = stdout.read().decode('utf-8', errors='ignore')
    
    if "Syntax OK" in test_result:
        print("[OK] Apache configuration is valid")
        
        # Restart Apache
        print("[4] Restarting Apache...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart apache2")
        time.sleep(3)
        
        # Check status
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active apache2")
        status = stdout.read().decode('utf-8').strip()
        if status == "active":
            print("[OK] Apache restarted successfully")
        else:
            print(f"[WARN] Apache status: {status}")
    else:
        print("[ERROR] Apache configuration test failed:")
        print(test_result)
        # Show the error
        print("\nFull test output:")
        print(test_result)
    
    print()
    print("=" * 80)
    print("[OK] LocationMatch fix complete!")
    print("=" * 80)

    ssh.close()

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()


"""
Completely remove LocationMatch and handle cache control differently
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
print("COMPLETELY REMOVING LocationMatch")
print("=" * 80)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {SERVER_HOST}...")
    ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    print("[OK] Connected!")
    print()

    config_path = "/etc/apache2/sites-available/000-default.conf"
    
    # Read config
    print("[1] Reading configuration...")
    stdin, stdout, stderr = ssh.exec_command(f"cat {config_path}")
    config_content = stdout.read().decode('utf-8', errors='ignore')
    
    # Create backup
    stdin, stdout, stderr = ssh.exec_command(f"cp {config_path} {config_path}.backup.$(date +%Y%m%d_%H%M%S)")
    print("[OK] Backup created")
    
    # Remove LocationMatch completely
    if '<LocationMatch' in config_content:
        print("[2] Removing LocationMatch block...")
        
        # Find LocationMatch block
        start = config_content.find('<LocationMatch')
        end = config_content.find('</LocationMatch>', start)
        
        if start != -1 and end != -1:
            # Remove the entire block including newlines
            before = config_content[:start].rstrip()
            after = config_content[end + len('</LocationMatch>'):].lstrip()
            
            # Remove any leading/trailing newlines
            new_config = before + '\n' + after
            
            # Write config
            print("[3] Writing updated configuration...")
            sftp = ssh.open_sftp()
            try:
                temp_file = f"{config_path}.new"
                with sftp.file(temp_file, 'w') as f:
                    f.write(new_config)
                
                stdin, stdout, stderr = ssh.exec_command(f"mv {temp_file} {config_path}")
                print("[OK] LocationMatch removed")
            finally:
                sftp.close()
        else:
            print("[WARN] Could not find LocationMatch block boundaries")
            new_config = config_content
    else:
        print("[OK] LocationMatch not found")
        new_config = config_content
    
    # Test Apache configuration
    print("[4] Testing Apache configuration...")
    stdin, stdout, stderr = ssh.exec_command("apache2ctl configtest 2>&1")
    test_result = stdout.read().decode('utf-8', errors='ignore')
    
    if "Syntax OK" in test_result:
        print("[OK] Apache configuration is valid")
        
        # Restart Apache
        print("[5] Restarting Apache...")
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
    
    print()
    print("=" * 80)
    print("[OK] LocationMatch removal complete!")
    print("=" * 80)

    ssh.close()

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()


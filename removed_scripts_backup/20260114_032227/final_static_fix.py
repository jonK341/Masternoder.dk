"""
Final fix - check SSL config and .htaccess files
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
print("FINAL STATIC FILES FIX - CHECK ALL CONFIGS")
print("=" * 80)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {SERVER_HOST}...")
    ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    print("[OK] Connected!")
    print()

    # Check SSL config for LocationMatch
    print("[1] Checking SSL config for LocationMatch...")
    ssl_config = "/etc/apache2/sites-available/000-default-le-ssl.conf"
    stdin, stdout, stderr = ssh.exec_command(f"grep -n 'LocationMatch\\|Location.*vidgenerator' {ssl_config}")
    ssl_location = stdout.read().decode('utf-8', errors='ignore')
    if ssl_location.strip():
        print("LocationMatch/Location found in SSL config:")
        print(ssl_location)
        
        # Remove it
        print("[2] Removing LocationMatch from SSL config...")
        stdin, stdout, stderr = ssh.exec_command(f"cp {ssl_config} {ssl_config}.backup.$(date +%Y%m%d_%H%M%S)")
        
        stdin, stdout, stderr = ssh.exec_command(f"cat {ssl_config}")
        ssl_content = stdout.read().decode('utf-8', errors='ignore')
        
        # Remove LocationMatch block
        if '<LocationMatch' in ssl_content:
            start = ssl_content.find('<LocationMatch')
            end = ssl_content.find('</LocationMatch>', start)
            if start != -1 and end != -1:
                new_ssl = ssl_content[:start].rstrip() + '\n' + ssl_content[end + len('</LocationMatch>'):].lstrip()
                
                sftp = ssh.open_sftp()
                try:
                    temp_file = f"{ssl_config}.new"
                    with sftp.file(temp_file, 'w') as f:
                        f.write(new_ssl)
                    stdin, stdout, stderr = ssh.exec_command(f"mv {temp_file} {ssl_config}")
                    print("[OK] LocationMatch removed from SSL config")
                finally:
                    sftp.close()
    else:
        print("[OK] No LocationMatch in SSL config")
    print()

    # Check for .htaccess files
    print("[3] Checking for .htaccess files...")
    htaccess_paths = [
        "/var/www/html/.htaccess",
        "/var/www/html/vidgenerator/.htaccess",
        "/var/www/html/vidgenerator/vidgenerator/.htaccess",
        "/var/www/html/vidgenerator/vidgenerator/static/.htaccess",
    ]
    for htaccess_path in htaccess_paths:
        stdin, stdout, stderr = ssh.exec_command(f"test -f {htaccess_path} && echo 'EXISTS' || echo 'MISSING'")
        result = stdout.read().decode('utf-8').strip()
        if "EXISTS" in result:
            print(f"[FOUND] {htaccess_path}")
            stdin, stdout, stderr = ssh.exec_command(f"cat {htaccess_path}")
            content = stdout.read().decode('utf-8', errors='ignore')
            print(content)
    print()

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
    print("[OK] Final fix complete!")
    print("=" * 80)

    ssh.close()

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()


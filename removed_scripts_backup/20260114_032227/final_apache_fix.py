#!/usr/bin/env python3
"""
Final Apache fix - ensure index.html is proxied correctly
"""
import paramiko
import os
import sys
import re

# Fix UnicodeEncodeError on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Server configuration
SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def final_fix():
    """Final fix - check DocumentRoot and ensure proper proxying"""
    print("="*80)
    print("FINAL APACHE FIX")
    print("="*80)
    
    # Connect to server
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=30)
        print(f"Connected to {SERVER_HOST}")
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return False
    
    try:
        config_file = '/etc/apache2/sites-available/000-default-le-ssl.conf'
        
        # Read current config
        stdin, stdout, stderr = ssh.exec_command(f"cat {config_file}")
        config_content = stdout.read().decode('utf-8')
        
        print("\nChecking current configuration...")
        
        # Check if Location directive exists
        if '<Location "/vidgenerator/index.html">' in config_content:
            print("  ✓ Location directive exists")
        else:
            print("  ✗ Location directive missing")
        
        # Check ProxyPass exclusion
        if 'ProxyPass /vidgenerator/index.html !' in config_content:
            print("  ✓ ProxyPass exclusion exists")
        else:
            print("  ✗ ProxyPass exclusion missing")
        
        # The issue might be that Location directive needs to be BEFORE ProxyPass
        # Let's reorganize the config to ensure proper order
        
        print("\n" + "="*80)
        print("REORGANIZING CONFIGURATION ORDER")
        print("="*80)
        
        # Create backup
        stdin, stdout, stderr = ssh.exec_command(f"cp {config_file} {config_file}.backup4")
        stdout.channel.recv_exit_status()
        print(f"  ✓ Backup created")
        
        lines = config_content.split('\n')
        new_lines = []
        
        # Reorganize: Location directives FIRST, then ProxyPass exclusions, then ProxyPass
        location_section = []
        proxypass_exclusions = []
        proxypass_main = []
        other_lines = []
        
        in_location = False
        current_location = []
        
        for i, line in enumerate(lines):
            if '<Location' in line:
                in_location = True
                current_location = [line]
            elif '</Location>' in line and in_location:
                current_location.append(line)
                location_section.extend(current_location)
                location_section.append('')  # Blank line
                in_location = False
                current_location = []
            elif in_location:
                current_location.append(line)
            elif 'ProxyPass /vidgenerator/index.html !' in line or 'ProxyPass /vidgenerator/static !' in line:
                proxypass_exclusions.append(line)
            elif 'ProxyPass /vidgenerator ' in line and '!' not in line:
                proxypass_main.append(line)
            elif 'ProxyPassReverse /vidgenerator' in line:
                proxypass_main.append(line)
            else:
                other_lines.append(line)
        
        # Rebuild config with proper order
        in_virtualhost = False
        for line in other_lines:
            new_lines.append(line)
            if '<VirtualHost' in line:
                in_virtualhost = True
            elif '</VirtualHost>' in line:
                # Insert our sections before closing VirtualHost
                if in_virtualhost:
                    # Add Location section
                    if location_section:
                        new_lines.append('    # Location directives for specific paths')
                        new_lines.extend(location_section)
                    
                    # Add ProxyPass exclusions
                    if proxypass_exclusions:
                        new_lines.append('    # ProxyPass exclusions (must be before ProxyPass)')
                        for excl in proxypass_exclusions:
                            new_lines.append(excl)
                        new_lines.append('')
                    
                    # Add main ProxyPass
                    if proxypass_main:
                        new_lines.append('    # Proxy other /vidgenerator requests to Flask')
                        for pp in proxypass_main:
                            new_lines.append(pp)
                    
                    in_virtualhost = False
                new_lines.append(line)
        
        # If we didn't find VirtualHost closing, just append at end
        if in_virtualhost:
            if location_section:
                new_lines.append('    # Location directives for specific paths')
                new_lines.extend(location_section)
            if proxypass_exclusions:
                new_lines.append('    # ProxyPass exclusions')
                for excl in proxypass_exclusions:
                    new_lines.append(excl)
            if proxypass_main:
                new_lines.append('    # Proxy other requests')
                for pp in proxypass_main:
                    new_lines.append(pp)
        
        # Write updated config
        new_content = '\n'.join(new_lines)
        
        # Write to temp file
        temp_file = f"{config_file}.tmp"
        stdin, stdout, stderr = ssh.exec_command(f"cat > {temp_file}")
        stdin.write(new_content)
        stdin.close()
        stdout.channel.recv_exit_status()
        
        # Validate syntax
        print(f"  Validating Apache configuration syntax...")
        stdin, stdout, stderr = ssh.exec_command(f"apache2ctl configtest")
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8')
        
        if 'Syntax OK' in output or exit_status == 0:
            print(f"  ✓ Configuration syntax is valid")
            # Move temp file to actual config
            stdin, stdout, stderr = ssh.exec_command(f"mv {temp_file} {config_file}")
            stdout.channel.recv_exit_status()
            print(f"  ✓ Configuration updated")
            
            # Restart Apache
            print(f"\nRestarting Apache...")
            stdin, stdout, stderr = ssh.exec_command("systemctl restart apache2")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                print("  ✓ Apache restarted successfully")
                print("\n" + "="*80)
                print("FINAL FIX COMPLETE")
                print("="*80)
                return True
            else:
                print("  ✗ Apache restart failed")
                return False
        else:
            print(f"  ✗ Configuration syntax error: {output}")
            ssh.exec_command(f"rm {temp_file}")
            return False
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    success = final_fix()
    exit(0 if success else 1)


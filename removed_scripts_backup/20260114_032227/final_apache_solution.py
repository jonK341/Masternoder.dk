#!/usr/bin/env python3
"""
Final solution - add Directory directive for index.html and ensure proper serving
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

def final_solution():
    """Final solution - add Directory directive and ensure file serving"""
    print("="*80)
    print("FINAL APACHE SOLUTION")
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
        
        # Create backup
        stdin, stdout, stderr = ssh.exec_command(f"cp {config_file} {config_file}.backup7")
        stdout.channel.recv_exit_status()
        print(f"  ✓ Backup created")
        
        lines = config_content.split('\n')
        new_lines = []
        added_directory = False
        
        # Add Directory directive after Alias for index.html
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            # After Alias /vidgenerator/index.html, add Directory directive
            if 'Alias /vidgenerator/index.html' in line and not added_directory:
                indent = len(line) - len(line.lstrip())
                directory_directive = [
                    ' ' * indent + '<Directory /var/www/html/vidgenerator/vidgenerator>',
                    ' ' * indent + '    Options -Indexes +FollowSymLinks',
                    ' ' * indent + '    AllowOverride None',
                    ' ' * indent + '    Require all granted',
                    ' ' * indent + '</Directory>',
                    ''
                ]
                new_lines.extend(directory_directive)
                print(f"  ✓ Added Directory directive after line {i+1}")
                added_directory = True
        
        if added_directory:
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
                    
                    # Test directly on server
                    print("\n" + "="*80)
                    print("TESTING ON SERVER")
                    print("="*80)
                    stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost/vidgenerator/index.html")
                    http_code = stdout.read().decode('utf-8').strip()
                    print(f"  Local test HTTP code: {http_code}")
                    
                    if http_code == '200':
                        print("  ✓ File is accessible locally!")
                    else:
                        print(f"  ✗ Still returning {http_code}")
                    
                    print("\n" + "="*80)
                    print("FINAL SOLUTION APPLIED")
                    print("="*80)
                    return True
                else:
                    print("  ✗ Apache restart failed")
                    return False
            else:
                print(f"  ✗ Configuration syntax error: {output}")
                ssh.exec_command(f"rm {temp_file}")
                return False
        else:
            print("  ⚠ Could not find insertion point for Directory directive")
            return False
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    success = final_solution()
    exit(0 if success else 1)


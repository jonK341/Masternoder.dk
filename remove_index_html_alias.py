#!/usr/bin/env python3
"""Remove Alias for index.html so RewriteRule can work"""
import paramiko
import os
import sys

# Fix UnicodeEncodeError on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Server configuration
SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def remove_alias():
    """Remove Alias for index.html"""
    print("="*80)
    print("REMOVING ALIAS FOR INDEX.HTML")
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
        stdin, stdout, stderr = ssh.exec_command(f"cp {config_file} {config_file}.backup9")
        stdout.channel.recv_exit_status()
        print(f"  ✓ Backup created")
        
        # Remove Alias line for index.html
        lines = config_content.split('\n')
        new_lines = []
        removed_alias = False
        
        for line in lines:
            if 'Alias /vidgenerator/index.html' in line:
                # Comment it out
                indent = len(line) - len(line.lstrip())
                commented = ' ' * indent + '# ' + line.lstrip() + '  # Commented out - using RewriteRule redirect instead'
                new_lines.append(commented)
                print(f"  ✓ Commented out Alias for index.html")
                removed_alias = True
            else:
                new_lines.append(line)
        
        if removed_alias:
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
                    print("ALIAS REMOVED - REWRITERULE SHOULD NOW WORK")
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
            print("  ⚠ Alias not found")
            return False
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    success = remove_alias()
    exit(0 if success else 1)


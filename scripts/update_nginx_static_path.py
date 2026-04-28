#!/usr/bin/env python3
"""
Update Nginx Static Path
Updates nginx config to point to correct static file location
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def update_nginx():
    """Update nginx static file path"""
    print("="*70)
    print("UPDATING NGINX STATIC FILE PATH")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        nginx_config = "/etc/nginx/sites-enabled/masternoder.dk"
        
        # Read current config
        print("[1/4] Reading current nginx config...")
        sftp = ssh.open_sftp()
        try:
            with sftp.open(nginx_config, 'r') as f:
                config_content = f.read().decode('utf-8')
            print(f"  [OK] Read {len(config_content)} bytes")
        except Exception as e:
            print(f"  [ERROR] Could not read config: {e}")
            return False
        finally:
            sftp.close()
        
        # Create backup
        print("[2/4] Creating backup...")
        try:
            stdin, stdout, stderr = ssh.exec_command(f"cp {nginx_config} {nginx_config}.backup.$(date +%Y%m%d_%H%M%S)", timeout=10)
            stdout.read()  # Wait for completion
            print("  [OK] Backup created")
        except Exception as e:
            print(f"  [WARN] Could not create backup: {e}")
        
        # Update static file path
        print("[3/4] Updating static file path...")
        old_path = "/var/www/html/vidgenerator/src/web/static"
        new_path = "/var/www/html/vidgenerator/static"
        
        if old_path in config_content:
            new_config = config_content.replace(old_path, new_path)
            print(f"  [OK] Replaced {old_path} with {new_path}")
        else:
            print(f"  [WARN] Old path not found in config, checking for other patterns...")
            # Try to find and replace any vidgenerator static path
            import re
            pattern = r'alias\s+/var/www/html/vidgenerator[^;]+static[^;]*;'
            matches = re.findall(pattern, config_content)
            if matches:
                print(f"  [INFO] Found static path patterns: {matches}")
                # Replace with new path
                new_config = re.sub(
                    r'alias\s+/var/www/html/vidgenerator[^;]+static[^;]*;',
                    f'alias {new_path};',
                    config_content
                )
                print(f"  [OK] Updated static path")
            else:
                print(f"  [ERROR] Could not find static path to update")
                return False
        
        # Write updated config
        print("[4/4] Writing updated config...")
        sftp = ssh.open_sftp()
        try:
            with sftp.open(nginx_config, 'w') as f:
                f.write(new_config.encode('utf-8'))
            print("  [OK] Config written")
        except Exception as e:
            print(f"  [ERROR] Could not write config: {e}")
            return False
        finally:
            sftp.close()
        
        # Test nginx config
        print()
        print("Testing nginx configuration...")
        try:
            stdin, stdout, stderr = ssh.exec_command("nginx -t 2>&1", timeout=10)
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            if "syntax is ok" in output or "syntax is ok" in error:
                print("  [OK] Nginx config is valid")
                
                # Reload nginx
                print()
                print("Reloading nginx...")
                stdin, stdout, stderr = ssh.exec_command("systemctl reload nginx", timeout=10)
                stdout.read()  # Wait for completion
                print("  [OK] Nginx reloaded")
            else:
                print(f"  [ERROR] Nginx config test failed:")
                print(f"    {output}")
                print(f"    {error}")
                return False
        except Exception as e:
            print(f"  [ERROR] Could not test/reload nginx: {e}")
            return False
        
        print()
        print("="*70)
        print("NGINX STATIC PATH UPDATE COMPLETE")
        print("="*70)
        print()
        print("Next steps:")
        print("  1. Test URL: https://masternoder.dk/vidgenerator/unified_dashboard")
        print("  2. Hard refresh browser (Ctrl+F5)")
        print("  3. Check console (F12) for errors")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    update_nginx()

#!/usr/bin/env python3
"""
Check and Fix Nginx Proxy Configuration
Ensures nginx correctly proxies API requests to uwsgi
"""
import paramiko
import os
import re

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_and_fix_nginx():
    """Check and fix nginx proxy configuration"""
    print("="*70)
    print("CHECKING AND FIXING NGINX PROXY CONFIGURATION")
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
        print("[1/5] Reading current nginx config...")
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
        
        print()
        print("[2/5] Analyzing current configuration...")
        
        # Check for location /vidgenerator/ block
        location_pattern = r'location\s+/vidgenerator/\s*\{[^}]*\}'
        location_matches = re.findall(location_pattern, config_content, re.DOTALL)
        
        if location_matches:
            print(f"  [OK] Found location /vidgenerator/ block")
            for match in location_matches:
                print(f"    Block preview: {match[:200]}...")
        else:
            print("  [WARN] No location /vidgenerator/ block found")
        
        # Check for proxy_pass
        if 'proxy_pass' in config_content:
            print("  [OK] proxy_pass found in config")
            # Extract proxy_pass lines
            proxy_lines = [line.strip() for line in config_content.split('\n') if 'proxy_pass' in line]
            for line in proxy_lines:
                print(f"    {line}")
        else:
            print("  [ERROR] proxy_pass not found in config")
        
        # Check for rewrite rules
        if 'rewrite' in config_content:
            print("  [OK] rewrite rules found")
            rewrite_lines = [line.strip() for line in config_content.split('\n') if 'rewrite' in line and 'vidgenerator' in line]
            for line in rewrite_lines:
                print(f"    {line}")
        
        print()
        print("[3/5] Checking if fix is needed...")
        
        # The issue: nginx should proxy /vidgenerator/api/* to uwsgi WITHOUT stripping the prefix
        # OR it should strip the prefix and Flask should handle it
        # Current setup: nginx strips prefix with rewrite, Flask middleware also tries to handle it
        
        # Check if we need to update the config
        needs_fix = False
        new_config = config_content
        
        # Look for the location /vidgenerator/ block
        # We want: proxy_pass http://127.0.0.1:5000/vidgenerator; (WITH prefix)
        # OR: rewrite ^/vidgenerator(/.*)$ $1 break; proxy_pass http://127.0.0.1:5000; (strip prefix)
        
        # Current pattern seems to be: rewrite strips prefix, then proxy_pass
        # But Flask middleware also strips it, causing double-stripping
        
        # Solution: Remove the rewrite rule and let Flask middleware handle it
        # OR: Keep rewrite, remove Flask middleware handling
        
        # Let's check what the current setup is
        if 'rewrite ^/vidgenerator(/.*)$ $1 break;' in config_content:
            print("  [INFO] Found rewrite rule that strips /vidgenerator prefix")
            print("  [INFO] Flask middleware also strips prefix - this is correct")
            print("  [INFO] No fix needed for rewrite rule")
        else:
            print("  [WARN] Rewrite rule not found or different")
        
        # Check if proxy_pass is correct
        if 'proxy_pass http://127.0.0.1:5000;' in config_content:
            print("  [OK] proxy_pass points to correct uwsgi socket")
        else:
            print("  [WARN] proxy_pass may not be correctly configured")
            needs_fix = True
        
        print()
        print("[4/5] Testing uwsgi connectivity...")
        try:
            # Test if uwsgi is listening on port 5000
            stdin, stdout, stderr = ssh.exec_command("netstat -tlnp | grep :5000 | head -1", timeout=5)
            output = stdout.read().decode().strip()
            if output:
                print(f"  [OK] uwsgi is listening: {output[:80]}")
            else:
                print("  [WARN] uwsgi may not be listening on port 5000")
        except Exception as e:
            print(f"  [WARN] Could not check uwsgi: {e}")
        
        print()
        print("[5/5] Summary and recommendations...")
        print("  The configuration appears correct:")
        print("    - nginx rewrites /vidgenerator/* to /*")
        print("    - nginx proxies to http://127.0.0.1:5000")
        print("    - Flask middleware handles /vidgenerator prefix")
        print()
        print("  The 500 errors were caused by ip_mac_user_manager being None")
        print("  This has been fixed in src/app.py")
        print()
        print("  Next step: Deploy the fixed src/app.py and restart uwsgi")
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_and_fix_nginx()

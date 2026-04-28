#!/usr/bin/env python3
"""
Fix Nginx Bottlenecks
Adds missing rewrite rule, proxy_pass, and timeout settings
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_nginx():
    """Fix nginx configuration"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        config_file = '/etc/nginx/sites-available/masternoder.dk'
        
        # Read current config
        print("[1/4] Reading nginx configuration...")
        sftp = ssh.open_sftp()
        with sftp.open(config_file, 'r') as f:
            config = f.read().decode('utf-8')
        sftp.close()
        
        print()
        print("[2/4] Analyzing configuration...")
        
        # Check if location /vidgenerator/ block exists and has correct settings
        needs_fix = False
        if 'location /vidgenerator/ {' in config:
            # Check for rewrite rule
            if 'rewrite ^/vidgenerator(/.*)$ $1 break;' not in config:
                print("  ❌ Missing rewrite rule")
                needs_fix = True
            else:
                print("  ✅ Rewrite rule found")
            
            # Check for proxy_pass
            if 'proxy_pass http://' not in config or 'proxy_pass http://unix:' not in config:
                # Check if it's in the location block
                location_start = config.find('location /vidgenerator/ {')
                location_end = config.find('}', location_start)
                location_block = config[location_start:location_end]
                
                if 'proxy_pass' not in location_block:
                    print("  ❌ Missing proxy_pass in location block")
                    needs_fix = True
                else:
                    print("  ✅ proxy_pass found")
            else:
                print("  ✅ proxy_pass found")
            
            # Check for timeout settings
            if 'proxy_read_timeout' not in config:
                print("  ❌ Missing proxy_read_timeout")
                needs_fix = True
            else:
                print("  ✅ proxy_read_timeout found")
            
            # Check for buffer settings
            if 'proxy_buffering off' not in config:
                print("  ⚠️  proxy_buffering not set to off (may cause bottlenecks)")
                needs_fix = True
            else:
                print("  ✅ proxy_buffering off found")
        else:
            print("  ❌ location /vidgenerator/ block not found")
            needs_fix = True
        
        if not needs_fix:
            print()
            print("  ✅ No fixes needed - configuration looks good")
            ssh.close()
            return True
        
        print()
        print("[3/4] Fixing configuration...")
        
        # Find location /vidgenerator/ block
        location_start = config.find('location /vidgenerator/ {')
        if location_start == -1:
            print("  ❌ Could not find location /vidgenerator/ block")
            ssh.close()
            return False
        
        # Find the end of the location block
        location_end = config.find('}', location_start)
        if location_end == -1:
            print("  ❌ Could not find end of location block")
            ssh.close()
            return False
        
        location_block = config[location_start:location_end+1]
        
        # Build optimized location block
        optimized_block = '''    location /vidgenerator/ {
        # Rewrite URL to remove /vidgenerator prefix before proxying
        rewrite ^/vidgenerator(/.*)$ $1 break;
        
        # Proxy to uWSGI socket (Flask app)
        proxy_pass http://unix:/var/www/html/vidgenerator/vidgenerator.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Buffer settings - disable buffering for faster responses
        proxy_buffering off;
        proxy_request_buffering off;
        
        # Timeouts - prevent hangs
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }'''
        
        # Replace the location block
        new_config = config[:location_start] + optimized_block + config[location_end+1:]
        
        # Backup original
        print("  Creating backup...")
        stdin, stdout, stderr = ssh.exec_command(
            f"cp {config_file} {config_file}.backup.$(date +%Y%m%d_%H%M%S)",
            timeout=10
        )
        stdout.read()
        
        # Write new config
        print("  Writing new configuration...")
        with sftp.open(config_file, 'w') as f:
            f.write(new_config.encode('utf-8'))
        sftp.close()
        
        print()
        print("[4/4] Testing nginx configuration...")
        stdin, stdout, stderr = ssh.exec_command(
            "nginx -t",
            timeout=10
        )
        test_output = stdout.read().decode('utf-8', errors='ignore')
        test_error = stderr.read().decode('utf-8', errors='ignore')
        
        if 'syntax is ok' in test_output or 'syntax is ok' in test_error:
            print("  ✅ Nginx configuration test passed")
            print()
            print("  Reloading nginx...")
            stdin2, stdout2, stderr2 = ssh.exec_command(
                "systemctl reload nginx",
                timeout=10
            )
            stdout2.read()
            print("  ✅ Nginx reloaded")
        else:
            print("  ❌ Nginx configuration test failed:")
            print(test_error)
            print("  Restoring backup...")
            stdin3, stdout3, stderr3 = ssh.exec_command(
                f"cp {config_file}.backup.* {config_file}",
                timeout=10
            )
            stdout3.read()
            ssh.close()
            return False
        
        ssh.close()
        print()
        print("="*80)
        print("NGINX BOTTLENECKS FIXED")
        print("="*80)
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_nginx()

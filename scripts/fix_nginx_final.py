#!/usr/bin/env python3
"""
Fix Nginx Final
Fixes nginx with correct uWSGI proxy_pass
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_nginx():
    """Fix nginx with correct proxy"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        nginx_config = "/etc/nginx/sites-enabled/masternoder.dk"
        
        # Create backup
        print("[1/4] Creating backup...")
        stdin, stdout, stderr = ssh.exec_command(
            f"cp {nginx_config} {nginx_config}.backup.$(date +%Y%m%d_%H%M%S)",
            timeout=10
        )
        stdout.read()
        print("  [OK] Backup created")
        
        # Location blocks template
        location_blocks = '''    # Static files
    location /vidgenerator/static {
        alias /var/www/html/vidgenerator/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Uploaded files
    location /vidgenerator/uploads {
        alias /var/www/html/vidgenerator/uploads;
        expires 7d;
    }

    # Output videos
    location /vidgenerator/output {
        alias /var/www/html/vidgenerator/output;
        expires 1d;
        add_header Content-Type "video/mp4";
    }

    # Redirect root to /vidgenerator/
    location = / {
        return 301 /vidgenerator/;
    }

    # Main application - proxy to Flask/uWSGI
    location /vidgenerator/ {
        # Rewrite URL to remove /vidgenerator prefix before proxying
        # This makes Flask see / instead of /vidgenerator/
        rewrite ^/vidgenerator(/.*)$ $1 break;

        # Proxy to uWSGI (listening on 127.0.0.1:5000)
        proxy_pass http://127.0.0.1:5000;
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

        # Buffer settings
        proxy_buffering off;
        proxy_request_buffering off;

        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Redirect /vidgenerator (without trailing slash) to /vidgenerator/
    location = /vidgenerator {
        return 301 /vidgenerator/;
    }'''
        
        # HTTPS server block
        https_server = f'''server {{
    listen 443 ssl http2;
    server_name masternoder.dk www.masternoder.dk;

    # SSL certificates (managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/masternoder.dk/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/masternoder.dk/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

{location_blocks}
}}

'''
        
        # HTTP server block (redirect to HTTPS)
        http_server = f'''server {{
    listen 80;
    server_name masternoder.dk www.masternoder.dk;

    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
}}

'''
        
        # Build new config
        new_config = https_server + http_server
        
        # Write the new config
        print()
        print("[2/4] Writing new config...")
        sftp = ssh.open_sftp()
        with sftp.open(nginx_config, 'w') as f:
            f.write(new_config.encode('utf-8'))
        sftp.close()
        print("  [OK] Config written")
        
        # Test nginx config
        print()
        print("[3/4] Testing nginx configuration...")
        stdin2, stdout2, stderr2 = ssh.exec_command("nginx -t 2>&1", timeout=10)
        output = stdout2.read().decode().strip()
        error = stderr2.read().decode().strip()
        
        if "syntax is ok" in output or "syntax is ok" in error:
            print("  [OK] Nginx config is valid")
            
            # Reload nginx
            print()
            print("[4/4] Reloading nginx...")
            stdin3, stdout3, stderr3 = ssh.exec_command("systemctl reload nginx", timeout=10)
            stdout3.read()
            print("  [OK] Nginx reloaded")
        else:
            print(f"  [ERROR] Nginx config test failed:")
            print(f"    {output}")
            print(f"    {error}")
            return False
        
        print()
        print("="*70)
        print("NGINX CONFIGURATION FIXED")
        print("="*70)
        print()
        print("✅ HTTPS server block (port 443) now has:")
        print("   - SSL configuration")
        print("   - Location blocks for static files, uploads, output")
        print("   - Location block for /vidgenerator/ with proxy_pass to uWSGI (127.0.0.1:5000)")
        print()
        print("✅ HTTP server block (port 80) redirects to HTTPS")
        print()
        print("Routes should now work via HTTPS!")
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_nginx()

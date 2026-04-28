#!/usr/bin/env python3
"""
Fix Nginx Server Blocks
Properly splits HTTP and HTTPS server blocks
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_nginx():
    """Fix nginx server blocks"""
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
        
        # Read the file
        print()
        print("[2/4] Reading config...")
        sftp = ssh.open_sftp()
        with sftp.open(nginx_config, 'r') as f:
            content = f.read().decode('utf-8')
        sftp.close()
        print(f"  [OK] Read config")
        
        # Build the new config with proper HTTP and HTTPS server blocks
        print()
        print("[3/4] Building new config...")
        
        # Location blocks template (same for both HTTP and HTTPS)
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

    # Main application - proxy to Flask
    location /vidgenerator/ {
        # Rewrite URL to remove /vidgenerator prefix before proxying
        # This makes Flask see / instead of /vidgenerator/
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
        print("[4/4] Writing new config...")
        sftp = ssh.open_sftp()
        with sftp.open(nginx_config, 'w') as f:
            f.write(new_config.encode('utf-8'))
        sftp.close()
        print("  [OK] Config written")
        
        # Test nginx config
        print()
        print("Testing nginx configuration...")
        stdin, stdout, stderr = ssh.exec_command("nginx -t 2>&1", timeout=10)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if "syntax is ok" in output or "syntax is ok" in error:
            print("  [OK] Nginx config is valid")
            
            # Reload nginx
            print()
            print("Reloading nginx...")
            stdin2, stdout2, stderr2 = ssh.exec_command("systemctl reload nginx", timeout=10)
            stdout2.read()
            print("  [OK] Nginx reloaded")
        else:
            print(f"  [ERROR] Nginx config test failed:")
            print(f"    {output}")
            print(f"    {error}")
            # Check if uWSGI socket exists
            print()
            print("Checking uWSGI socket...")
            stdin3, stdout3, stderr3 = ssh.exec_command("ls -la /var/www/html/vidgenerator/*.sock 2>&1", timeout=5)
            socket_info = stdout3.read().decode().strip()
            print(f"  Socket info: {socket_info}")
            return False
        
        print()
        print("="*70)
        print("NGINX SERVER BLOCKS FIXED")
        print("="*70)
        print()
        print("HTTPS server block now has:")
        print("  - SSL configuration")
        print("  - Location blocks for /vidgenerator/static, /vidgenerator/uploads, /vidgenerator/output")
        print("  - Location block for /vidgenerator/ with proxy_pass to uWSGI")
        print()
        print("HTTP server block redirects to HTTPS")
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_nginx()

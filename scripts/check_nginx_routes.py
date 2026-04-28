#!/usr/bin/env python3
"""
Check Nginx Routes
Verify nginx configuration is correct for profile and other routes
"""
import paramiko
import os

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def check_nginx():
    """Check nginx configuration"""
    print("=" * 70)
    print("CHECKING NGINX ROUTES")
    print("=" * 70)
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        # Find nginx config file
        print("[1/3] Finding nginx config file...")
        config_paths = [
            '/etc/nginx/sites-available/masternoder.dk',
            '/etc/nginx/sites-available/default',
            '/etc/nginx/nginx.conf',
        ]
        
        config_file = None
        for path in config_paths:
            cmd = f"test -f {path} && echo 'EXISTS' || echo 'NOT FOUND'"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            result = stdout.read().decode('utf-8').strip()
            if result == 'EXISTS':
                config_file = path
                print(f"  [OK] Found: {path}")
                break
        
        if not config_file:
            print("  [WARN] Could not find nginx config file")
            ssh.close()
            return
        
        print()
        
        # Read config
        print(f"[2/3] Reading nginx config from {config_file}...")
        stdin, stdout, stderr = ssh.exec_command(f"cat {config_file}", timeout=10)
        config = stdout.read().decode('utf-8')
        
        # Check for key routes
        checks = {
            'location /vidgenerator/': 'location /vidgenerator/' in config,
            'proxy_pass': 'proxy_pass' in config,
            'rewrite ^/vidgenerator': 'rewrite ^/vidgenerator' in config,
            'Cache-Control headers': 'Cache-Control' in config or 'no-cache' in config,
            'profile route': '/vidgenerator/profile' in config or 'location /vidgenerator/' in config,
        }
        
        print("\n  Route Configuration:")
        for check, found in checks.items():
            status = "[OK]" if found else "[MISS]"
            print(f"    {status} {check}: {found}")
        
        # Check proxy_pass target
        print("\n  Proxy Configuration:")
        if 'proxy_pass' in config:
            import re
            proxy_matches = re.findall(r'proxy_pass\s+([^;]+);', config)
            for match in proxy_matches:
                print(f"    proxy_pass: {match.strip()}")
        
        # Check for cache headers in location blocks
        print("\n  Cache Headers:")
        if 'Cache-Control' in config or 'no-cache' in config:
            cache_lines = [line for line in config.split('\n') if 'Cache-Control' in line or 'no-cache' in line]
            for line in cache_lines[:5]:
                print(f"    {line.strip()}")
        else:
            print("    [WARN] No cache headers found in location blocks")
            print("    [INFO] Consider adding cache headers for profile page")
        
        print()
        
        # Check nginx status
        print("[3/3] Checking nginx status...")
        stdin, stdout, stderr = ssh.exec_command("systemctl status nginx 2>&1 | head -5", timeout=10)
        status = stdout.read().decode('utf-8')
        if 'active (running)' in status:
            print("  [OK] Nginx is running")
        else:
            print(f"  [WARN] Nginx status: {status[:100]}")
        
        # Test config
        stdin, stdout, stderr = ssh.exec_command("nginx -t 2>&1", timeout=10)
        test_result = stdout.read().decode('utf-8')
        if 'syntax is ok' in test_result:
            print("  [OK] Nginx config test passed")
        else:
            print(f"  [WARN] Nginx config test: {test_result[:200]}")
        
        print()
        print("=" * 70)
        print("NGINX CHECK COMPLETE")
        print("=" * 70)
        
        # Recommendations
        if not checks.get('Cache-Control headers'):
            print("\n[RECOMMENDATION]")
            print("  Consider adding cache-busting headers to profile route:")
            print("    add_header Cache-Control 'no-cache, no-store, must-revalidate';")
            print("    add_header Pragma 'no-cache';")
            print("    add_header Expires '0';")
        
        ssh.close()
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_nginx()

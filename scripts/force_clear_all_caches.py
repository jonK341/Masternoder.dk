#!/usr/bin/env python3
"""
Force Clear All Caches
Aggressively clear all caches including Nginx, Python, and template caches
"""
import paramiko
import os

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def clear_all_caches():
    """Clear all caches aggressively"""
    print("=" * 70)
    print("FORCE CLEARING ALL CACHES")
    print("=" * 70)
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        commands = [
            # Clear Python cache
            ("find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true", "Python cache"),
            ("find /var/www/html/vidgenerator -name '*.pyc' -delete 2>/dev/null || true", "Python bytecode"),
            
            # Clear Nginx cache
            ("rm -rf /var/cache/nginx/* 2>/dev/null || true", "Nginx cache"),
            ("rm -rf /var/lib/nginx/cache/* 2>/dev/null || true", "Nginx lib cache"),
            
            # Clear template cache (if Flask is caching)
            ("find /var/www/html/vidgenerator -name '*.htmlc' -delete 2>/dev/null || true", "HTML cache files"),
            
            # Touch the profile file to update timestamp
            ("touch /var/www/html/vidgenerator/profile/index.html", "Update profile file timestamp"),
            
            # Reload Nginx
            ("nginx -s reload 2>&1 || systemctl reload nginx 2>&1 || true", "Reload Nginx"),
        ]
        
        for cmd, desc in commands:
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
                exit_status = stdout.channel.recv_exit_status()
                output = stdout.read().decode('utf-8', errors='ignore')
                error = stderr.read().decode('utf-8', errors='ignore')
                
                if exit_status == 0 or 'true' in cmd:
                    print(f"  [OK] {desc}")
                else:
                    print(f"  [WARN] {desc}: exit {exit_status}")
                    if error:
                        print(f"    Error: {error[:100]}")
            except Exception as e:
                print(f"  [WARN] {desc}: {e}")
        
        print()
        print("=" * 70)
        print("CACHE CLEAR COMPLETE")
        print("=" * 70)
        
        ssh.close()
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    clear_all_caches()

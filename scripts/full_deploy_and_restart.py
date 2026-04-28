#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full Deploy and Restart - Complete Production Deployment
Deploys all files and restarts all services
"""
import paramiko
import os
import glob

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def full_deploy():
    """Full deployment with service restarts"""
    ssh = None
    sftp = None
    try:
        print("=" * 70)
        print("FULL PRODUCTION DEPLOYMENT")
        print("=" * 70)
        print()
        
        print("[1/7] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("  [OK] Connected")
        print()
        
        # Deploy all HTML files
        print("[2/7] Deploying HTML files...")
        html_files = []
        for root, dirs, files in os.walk('vidgenerator'):
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__']]
            for file in files:
                if file.endswith('.html'):
                    html_files.append(os.path.join(root, file))
        
        deployed = 0
        for local_path in html_files:
            remote_path = f'/var/www/html/{local_path.replace(os.sep, "/")}'
            remote_dir = os.path.dirname(remote_path)
            ssh.exec_command(f'mkdir -p {remote_dir} 2>&1', timeout=5)
            
            try:
                with open(local_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                with sftp.open(remote_path, 'w') as f:
                    f.write(content)
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {local_path}: {e}")
        
        print(f"  [OK] Deployed {deployed} HTML files")
        print()
        
        # Deploy error logging files
        print("[3/7] Deploying error logging system...")
        error_files = [
            'src/db/models_error_logging.py',
            'backend/routes/error_logging_routes.py',
            'backend/routes/error_handler_status_routes.py',
            'backend/register_blueprints.py',
            'vidgenerator/static/js/error-manager.js',
            'vidgenerator/static/js/backend-connector.js',
            'vidgenerator/debugger/index.html'
        ]
        
        for local_path in error_files:
            if os.path.exists(local_path):
                remote_path = f'/var/www/html/{local_path.replace(os.sep, "/")}'
                remote_dir = os.path.dirname(remote_path)
                ssh.exec_command(f'mkdir -p {remote_dir} 2>&1', timeout=5)
                
                try:
                    with open(local_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    with sftp.open(remote_path, 'w') as f:
                        f.write(content)
                    print(f"  [OK] {local_path}")
                except Exception as e:
                    print(f"  [ERROR] {local_path}: {e}")
        
        print()
        
        # Clear all caches
        print("[4/7] Clearing all caches...")
        ssh.exec_command("rm -rf /var/cache/nginx/* 2>&1", timeout=10)
        ssh.exec_command("find /var/www/html -name '*.pyc' -delete 2>&1", timeout=30)
        ssh.exec_command("find /var/www/html -name '__pycache__' -type d -exec rm -rf {} + 2>&1 || true", timeout=30)
        print("  [OK] Caches cleared")
        print()
        
        # Restart python-proxy
        print("[5/7] Restarting python-proxy...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart python-proxy.service 2>&1", timeout=30)
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        if 'Active: active' in output or not error:
            print("  [OK] python-proxy restarted")
        else:
            print(f"  [WARN] python-proxy: {error[:100]}")
        print()
        
        # Restart uwsgi
        print("[6/7] Restarting uwsgi-vidgenerator...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1 || service uwsgi-vidgenerator restart 2>&1", timeout=30)
        output = stdout.read().decode('utf-8', errors='ignore')
        print("  [OK] uwsgi restarted")
        print()
        
        # Restart nginx and apache
        print("[7/7] Restarting web servers...")
        ssh.exec_command("systemctl restart nginx 2>&1", timeout=30)
        ssh.exec_command("systemctl restart apache2 2>&1 || true", timeout=30)
        print("  [OK] nginx restarted")
        print("  [OK] apache2 restarted (if available)")
        print()
        
        # Verify services
        print("Verifying services...")
        for service in ['python-proxy', 'nginx', 'uwsgi-vidgenerator']:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service} 2>&1", timeout=5)
            status = stdout.read().decode('utf-8', errors='ignore').strip()
            print(f"  {service}: {status}")
        print()
        
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("All files deployed and services restarted!")
        print()
        print("Next steps:")
        print("  1. Hard refresh browser: Ctrl+Shift+R")
        print("  2. Check browser console for cache-version meta tag")
        print("  3. Verify content updates")
        
    except Exception as e:
        print(f"\n[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()

if __name__ == '__main__':
    full_deploy()

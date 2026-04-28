"""
Deploy Universal Integrations
Deploy auto-save status and top 50 frame to all pages
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def deploy_all():
    """Deploy universal integrations"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*70)
        print("DEPLOYING UNIVERSAL INTEGRATIONS")
        print("="*70)
        
        files_to_deploy = [
            ('vidgenerator/static/js/universal-auto-save-status.js', '/var/www/html/vidgenerator/vidgenerator/static/js/universal-auto-save-status.js'),
            ('vidgenerator/index.html', '/var/www/html/vidgenerator/vidgenerator/index.html'),
            ('vidgenerator/battle/index.html', '/var/www/html/vidgenerator/vidgenerator/battle/index.html'),
            ('vidgenerator/generator/index.html', '/var/www/html/vidgenerator/vidgenerator/generator/index.html'),
            ('vidgenerator/stats/index.html', '/var/www/html/vidgenerator/vidgenerator/stats/index.html'),
            ('vidgenerator/game/index.html', '/var/www/html/vidgenerator/vidgenerator/game/index.html'),
            ('vidgenerator/profile/index.html', '/var/www/html/vidgenerator/vidgenerator/profile/index.html'),
        ]
        
        print("\n[STEP 1] Deploying files...")
        for local_path, remote_path in files_to_deploy:
            if os.path.exists(local_path):
                with open(local_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                remote_dir = os.path.dirname(remote_path)
                stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
                stdout.channel.recv_exit_status()
                
                stdin, stdout, stderr = ssh.exec_command(f"cat > {remote_path} << 'ENDOFFILE'\n{content}\nENDOFFILE")
                exit_status = stdout.channel.recv_exit_status()
                
                if exit_status == 0:
                    print(f"  [OK] {local_path}")
                else:
                    error = stderr.read().decode('utf-8', errors='ignore')
                    print(f"  [ERROR] {local_path}: {error[:200]}")
            else:
                print(f"  [WARN] Not found: {local_path}")
        
        print("\n[STEP 2] Clearing cache...")
        commands = [
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true",
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("  [OK] Cache cleared")
        
        ssh.close()
        
        print("\n" + "="*70)
        print("DEPLOYMENT COMPLETE")
        print("="*70)
        print("\n[INFO] Universal integrations deployed:")
        print("  [OK] Auto-save status to all pages")
        print("  [OK] Top 50 frame to major pages")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_all()


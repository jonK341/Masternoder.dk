"""
Deploy Battle and Calculator Updates
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def deploy_all():
    """Deploy battle and calculator updates"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*70)
        print("DEPLOYING BATTLE & CALCULATOR UPDATES")
        print("="*70)
        
        files_to_deploy = [
            ('vidgenerator/battle/index.html', '/var/www/html/vidgenerator/vidgenerator/battle/index.html'),
            ('vidgenerator/advanced_calculator/index.html', '/var/www/html/vidgenerator/vidgenerator/advanced_calculator/index.html'),
            ('vidgenerator/static/js/insane-battle-integration.js', '/var/www/html/vidgenerator/vidgenerator/static/js/insane-battle-integration.js'),
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
        print("\n[INFO] Updates deployed:")
        print("  [OK] Battle page with insane battle buttons")
        print("  [OK] Advanced calculator with enhanced atomic calculator")
        print("  [OK] Insane battle integration JavaScript")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_all()


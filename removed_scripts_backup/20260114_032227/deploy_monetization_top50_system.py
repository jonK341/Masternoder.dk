"""
Deploy Monetization, Top 50, Trophies, Knowledge, and Insane Battles
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def deploy_all():
    """Deploy all monetization systems"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*70)
        print("DEPLOYING MONETIZATION & TOP 50 SYSTEM")
        print("="*70)
        
        files_to_deploy = [
            ('backend/services/monetization_cash_generator.py', '/var/www/html/vidgenerator/backend/services/monetization_cash_generator.py'),
            ('backend/services/victory_trophy_generator.py', '/var/www/html/vidgenerator/backend/services/victory_trophy_generator.py'),
            ('backend/services/tech_tree_knowledge.py', '/var/www/html/vidgenerator/backend/services/tech_tree_knowledge.py'),
            ('backend/services/insane_battle_system.py', '/var/www/html/vidgenerator/backend/services/insane_battle_system.py'),
            ('backend/routes/monetization_top50_routes.py', '/var/www/html/vidgenerator/backend/routes/monetization_top50_routes.py'),
            ('vidgenerator/static/js/top50-monetization-frame.js', '/var/www/html/vidgenerator/vidgenerator/static/js/top50-monetization-frame.js'),
            ('vidgenerator/index.html', '/var/www/html/vidgenerator/vidgenerator/index.html'),
            ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
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
        
        print("\n[STEP 3] Restarting uWSGI...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart uwsgi")
        stdout.channel.recv_exit_status()
        print("  [OK] uWSGI restarted")
        time.sleep(15)
        
        ssh.close()
        
        print("\n" + "="*70)
        print("DEPLOYMENT COMPLETE")
        print("="*70)
        print("\n[INFO] Systems deployed:")
        print("  [OK] Monetization cash generator")
        print("  [OK] Top 50 leaderboard")
        print("  [OK] Top 6 trophies & resources")
        print("  [OK] Tech tree knowledge system")
        print("  [OK] Insane battle system")
        print("  [OK] Top 50 frame with toggle switch")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_all()


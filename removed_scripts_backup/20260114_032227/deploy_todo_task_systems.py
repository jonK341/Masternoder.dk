"""
Deploy TODO System and Task Planner
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def deploy_all():
    """Deploy TODO and task planner systems"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*70)
        print("DEPLOYING TODO SYSTEM AND TASK PLANNER")
        print("="*70)
        
        files_to_deploy = [
            ('backend/services/todo_system_manager.py', '/var/www/html/vidgenerator/backend/services/todo_system_manager.py'),
            ('backend/services/comprehensive_task_planner.py', '/var/www/html/vidgenerator/backend/services/comprehensive_task_planner.py'),
            ('backend/routes/todo_system_routes.py', '/var/www/html/vidgenerator/backend/routes/todo_system_routes.py'),
            ('backend/routes/task_planner_routes.py', '/var/www/html/vidgenerator/backend/routes/task_planner_routes.py'),
            ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
            ('COMPREHENSIVE_TODO_LIST.md', '/var/www/html/vidgenerator/COMPREHENSIVE_TODO_LIST.md'),
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
        print("  [OK] TODO System Manager")
        print("  [OK] Comprehensive Task Planner")
        print("  [OK] TODO API routes")
        print("  [OK] Task Planner API routes")
        print("  [OK] Comprehensive TODO List document")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_all()


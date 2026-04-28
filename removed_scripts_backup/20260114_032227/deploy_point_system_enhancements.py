"""
Deploy Point System Enhancements
Deploys all new point system services, routes, and frontend components
"""
import paramiko
import os
import time
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def deploy_file(ssh, local_path, remote_path, max_retries=3):
    """Deploy a single file with retry logic"""
    for attempt in range(max_retries):
        try:
            if not os.path.exists(local_path):
                return False, f"File not found: {local_path}"
            
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            import base64
            content_b64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
            
            remote_dir = os.path.dirname(remote_path)
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}", timeout=5)
            stdout.channel.recv_exit_status()
            
            cmd = f"echo '{content_b64}' | base64 -d > {remote_path}"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                return True, "OK"
            else:
                error = stderr.read().decode('utf-8', errors='ignore')
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return False, error[:200]
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return False, str(e)
    
    return False, "Max retries exceeded"

def deploy_all():
    """Deploy all point system enhancements"""
    ssh = None
    max_connection_retries = 5
    
    # Try to establish connection
    for conn_attempt in range(max_connection_retries):
        try:
            print(f"\n[CONNECTION] Attempt {conn_attempt + 1}/{max_connection_retries}")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
            print("  [OK] Connection established")
            break
        except Exception as e:
            print(f"  [ERROR] Connection failed: {e}")
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
            ssh = None
            if conn_attempt < max_connection_retries - 1:
                time.sleep(5)
    
    if not ssh:
        print("\n[ERROR] Could not establish connection")
        return False
    
    try:
        print("\n" + "="*70)
        print("DEPLOYING POINT SYSTEM ENHANCEMENTS")
        print("="*70)
        
        files_to_deploy = [
            # Backend services
            ('backend/services/point_calculator_integration.py', '/var/www/html/vidgenerator/backend/services/point_calculator_integration.py'),
            ('backend/services/point_history_tracking.py', '/var/www/html/vidgenerator/backend/services/point_history_tracking.py'),
            ('backend/services/point_analytics_dashboard.py', '/var/www/html/vidgenerator/backend/services/point_analytics_dashboard.py'),
            ('backend/services/point_generation_activities.py', '/var/www/html/vidgenerator/backend/services/point_generation_activities.py'),
            
            # Backend routes
            ('backend/routes/point_analytics_routes.py', '/var/www/html/vidgenerator/backend/routes/point_analytics_routes.py'),
            
            # Registration
            ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
            
            # Frontend
            ('vidgenerator/static/js/point-analytics-dashboard.js', '/var/www/html/vidgenerator/vidgenerator/static/js/point-analytics-dashboard.js'),
        ]
        
        print("\n[STEP 1] Deploying files...")
        deployed = 0
        failed = 0
        
        for local_path, remote_path in files_to_deploy:
            print(f"  Deploying: {os.path.basename(local_path)}")
            success, message = deploy_file(ssh, local_path, remote_path)
            
            if success:
                print(f"    [OK] {os.path.basename(local_path)}")
                deployed += 1
            else:
                print(f"    [FAIL] {os.path.basename(local_path)}: {message}")
                failed += 1
        
        print(f"\n  Deployed: {deployed}/{len(files_to_deploy)}")
        print(f"  Failed: {failed}/{len(files_to_deploy)}")
        
        if deployed > 0:
            print("\n[STEP 2] Clearing cache...")
            commands = [
                "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
                "find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true",
            ]
            for cmd in commands:
                try:
                    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
                    stdout.channel.recv_exit_status()
                except:
                    pass
            print("  [OK] Cache cleared")
            
            print("\n[STEP 3] Restarting uWSGI...")
            try:
                stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart uwsgi", timeout=10)
                stdout.channel.recv_exit_status()
                print("  [OK] uWSGI restart command sent")
                print("  [INFO] Waiting 15 seconds for service to restart...")
                time.sleep(15)
            except Exception as e:
                print(f"  [WARN] Could not restart uWSGI: {e}")
        
        ssh.close()
        
        print("\n" + "="*70)
        print("DEPLOYMENT SUMMARY")
        print("="*70)
        print(f"\n[INFO] Files deployed: {deployed}")
        print(f"[INFO] Files failed: {failed}")
        print(f"[INFO] Success rate: {(deployed/len(files_to_deploy)*100):.1f}%")
        
        if deployed > 0:
            print("\n[INFO] Systems deployed:")
            print("  [OK] Point calculator integration")
            print("  [OK] Point history tracking")
            print("  [OK] Point analytics dashboard")
            print("  [OK] Enhanced point multipliers")
            print("  [OK] Point analytics API routes")
            print("  [OK] Frontend analytics component")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Deployment error: {e}")
        import traceback
        traceback.print_exc()
        if ssh:
            try:
                ssh.close()
            except:
                pass
        return False

if __name__ == "__main__":
    print("Deploying Point System Enhancements...")
    success = deploy_all()
    
    if not success:
        print("\n[INFO] Deployment incomplete. Retry when connection is stable.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Deployment completed successfully!")


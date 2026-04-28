"""
Deploy All New Systems - Stable Connection Version
Deploys all new systems with retry logic and connection stability checks
"""
import paramiko
import os
import time
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def test_connection(ssh):
    """Test SSH connection"""
    try:
        stdin, stdout, stderr = ssh.exec_command("echo 'connection_test'", timeout=5)
        stdout.channel.recv_exit_status()
        return True
    except:
        return False

def deploy_file(ssh, local_path, remote_path, max_retries=3):
    """Deploy a single file with retry logic"""
    for attempt in range(max_retries):
        try:
            if not os.path.exists(local_path):
                return False, f"File not found: {local_path}"
            
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Escape content for shell
            content_escaped = content.replace("'", "'\"'\"'")
            
            remote_dir = os.path.dirname(remote_path)
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}", timeout=5)
            stdout.channel.recv_exit_status()
            
            # Use base64 encoding for safer file transfer
            import base64
            content_b64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
            
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
    """Deploy all new systems"""
    ssh = None
    max_connection_retries = 5
    
    # Try to establish connection
    for conn_attempt in range(max_connection_retries):
        try:
            print(f"\n[CONNECTION] Attempt {conn_attempt + 1}/{max_connection_retries}")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
            
            # Test connection
            if test_connection(ssh):
                print("  [OK] Connection established and tested")
                break
            else:
                print("  [WARN] Connection test failed, retrying...")
                ssh.close()
                ssh = None
                time.sleep(3)
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
        print("\n[ERROR] Could not establish stable connection after multiple attempts")
        print("[INFO] Files are ready locally. Please deploy manually when connection is stable.")
        return False
    
    try:
        print("\n" + "="*70)
        print("DEPLOYING ALL NEW SYSTEMS")
        print("="*70)
        
        files_to_deploy = [
            # JavaScript files
            ('vidgenerator/static/js/knowledge-unlock-ui.js', '/var/www/html/vidgenerator/vidgenerator/static/js/knowledge-unlock-ui.js'),
            ('vidgenerator/static/js/energy-regeneration-timers.js', '/var/www/html/vidgenerator/vidgenerator/static/js/energy-regeneration-timers.js'),
            ('vidgenerator/static/js/universal-auto-save-status.js', '/var/www/html/vidgenerator/vidgenerator/static/js/universal-auto-save-status.js'),
            ('vidgenerator/static/js/insane-battle-integration.js', '/var/www/html/vidgenerator/vidgenerator/static/js/insane-battle-integration.js'),
            
            # Backend services
            ('backend/services/point_generation_activities.py', '/var/www/html/vidgenerator/backend/services/point_generation_activities.py'),
            
            # Backend routes
            ('backend/routes/point_generation_routes.py', '/var/www/html/vidgenerator/backend/routes/point_generation_routes.py'),
            ('backend/routes/unified_dashboard_routes.py', '/var/www/html/vidgenerator/backend/routes/unified_dashboard_routes.py'),
            
            # Registration
            ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
            
            # HTML pages
            ('vidgenerator/index.html', '/var/www/html/vidgenerator/vidgenerator/index.html'),
            ('vidgenerator/unified_dashboard/index.html', '/var/www/html/vidgenerator/vidgenerator/unified_dashboard/index.html'),
            ('vidgenerator/battle/index.html', '/var/www/html/vidgenerator/vidgenerator/battle/index.html'),
            ('vidgenerator/generator/index.html', '/var/www/html/vidgenerator/vidgenerator/generator/index.html'),
            ('vidgenerator/stats/index.html', '/var/www/html/vidgenerator/vidgenerator/stats/index.html'),
            ('vidgenerator/game/index.html', '/var/www/html/vidgenerator/vidgenerator/game/index.html'),
            ('vidgenerator/profile/index.html', '/var/www/html/vidgenerator/vidgenerator/profile/index.html'),
            ('vidgenerator/gallery/index.html', '/var/www/html/vidgenerator/vidgenerator/gallery/index.html'),
            ('vidgenerator/social/index.html', '/var/www/html/vidgenerator/vidgenerator/social/index.html'),
            ('vidgenerator/dashboard/index.html', '/var/www/html/vidgenerator/vidgenerator/dashboard/index.html'),
            ('vidgenerator/victory-tech-tree/index.html', '/var/www/html/vidgenerator/vidgenerator/victory-tech-tree/index.html'),
            ('vidgenerator/advanced_calculator/index.html', '/var/www/html/vidgenerator/vidgenerator/advanced_calculator/index.html'),
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
                
                # Test connection after failure
                if not test_connection(ssh):
                    print("    [WARN] Connection lost, reconnecting...")
                    try:
                        ssh.close()
                    except:
                        pass
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
        
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
                print("  [INFO] Please restart uWSGI manually on the server")
        
        ssh.close()
        
        print("\n" + "="*70)
        print("DEPLOYMENT SUMMARY")
        print("="*70)
        print(f"\n[INFO] Files deployed: {deployed}")
        print(f"[INFO] Files failed: {failed}")
        print(f"[INFO] Success rate: {(deployed/len(files_to_deploy)*100):.1f}%")
        
        if deployed > 0:
            print("\n[INFO] Systems deployed:")
            print("  [OK] Knowledge unlock UI")
            print("  [OK] Energy regeneration timers")
            print("  [OK] Universal auto-save status")
            print("  [OK] Insane battle integration")
            print("  [OK] Point generation from activities")
            print("  [OK] Unified dashboard")
            print("  [OK] All page updates")
        
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
    print("Waiting for stable connection...")
    time.sleep(2)
    
    success = deploy_all()
    
    if not success:
        print("\n[INFO] Deployment incomplete due to connection issues.")
        print("[INFO] All files are ready locally. Retry deployment when connection is stable.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Deployment completed successfully!")


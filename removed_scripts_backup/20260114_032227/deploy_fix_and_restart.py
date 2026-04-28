"""
Deploy fixed auto-save routes and restart uWSGI
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def deploy_and_restart():
    """Deploy fixed file and restart"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*70)
        print("DEPLOYING FIXED AUTO-SAVE ROUTES AND RESTARTING")
        print("="*70)
        
        # Read and deploy fixed file
        with open('backend/routes/comprehensive_auto_save_routes.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        remote_path = '/var/www/html/vidgenerator/backend/routes/comprehensive_auto_save_routes.py'
        remote_dir = os.path.dirname(remote_path)
        
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
        stdout.channel.recv_exit_status()
        
        stdin, stdout, stderr = ssh.exec_command(f"cat > {remote_path} << 'ENDOFFILE'\n{content}\nENDOFFILE")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print(f"  [OK] Deployed fixed comprehensive_auto_save_routes.py")
        else:
            error = stderr.read().decode('utf-8', errors='ignore')
            print(f"  [ERROR] {error[:200]}")
        
        # Clear cache
        print("\n[STEP 2] Clearing Python cache...")
        commands = [
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true",
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("  [OK] Cache cleared")
        
        # Restart uWSGI
        print("\n[STEP 3] Restarting uWSGI...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart uwsgi")
        stdout.channel.recv_exit_status()
        print("  [OK] uWSGI restarted")
        time.sleep(15)  # Wait longer for app to load
        
        # Test endpoints
        print("\n[STEP 4] Testing endpoints...")
        endpoints = [
            ("/vidgenerator/api/auto-save/status?user_id=test", "Auto-Save Status"),
        ]
        
        for endpoint, name in endpoints:
            print(f"\n  [TEST] {name}")
            cmd = f"curl -s -w '\\nHTTP_CODE:%{{http_code}}' 'https://masternoder.dk{endpoint}'"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode('utf-8', errors='ignore')
            
            if "HTTP_CODE:200" in output:
                print(f"    [SUCCESS] Status 200")
                print(f"    Response: {output.split('HTTP_CODE')[0][:100]}")
            elif "HTTP_CODE:404" in output:
                print(f"    [FAIL] Status 404")
            else:
                print(f"    [INFO] {output[-100:]}")
        
        ssh.close()
        
        print("\n" + "="*70)
        print("DEPLOYMENT COMPLETE")
        print("="*70)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_and_restart()


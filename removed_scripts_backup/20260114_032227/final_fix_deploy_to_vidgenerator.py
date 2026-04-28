"""
Final Fix: Deploy Files to vidgenerator Directory
uWSGI runs from /var/www/html/vidgenerator, so we need to ensure files are there
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def deploy_to_vidgenerator():
    """Deploy files to vidgenerator directory"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*60)
        print("DEPLOYING TO VIDGENERATOR DIRECTORY")
        print("="*60)
        
        # Files to copy from /var/www/html to /var/www/html/vidgenerator
        files_to_sync = [
            "backend/routes/unified_game_mechanics_routes.py",
            "backend/routes/ultra_resource_controller_routes.py",
            "backend/routes/enhanced_systems_routes.py",
            "backend/routes/new_systems_routes.py",
            "backend/register_blueprints.py",
            "backend/services/unified_game_mechanics_constructor.py",
            "backend/services/ultra_resource_controller.py",
        ]
        
        print("\n[STEP 1] Syncing files to vidgenerator directory...")
        synced = 0
        for file_path in files_to_sync:
            source = f"/var/www/html/{file_path}"
            dest = f"/var/www/html/vidgenerator/{file_path}"
            dest_dir = os.path.dirname(dest)
            
            # Create directory if needed
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {dest_dir}")
            stdout.channel.recv_exit_status()
            
            # Copy file
            stdin, stdout, stderr = ssh.exec_command(f"cp {source} {dest} 2>&1")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                print(f"  [OK] {file_path}")
                synced += 1
            else:
                error = stderr.read().decode()
                print(f"  [FAIL] {file_path}: {error[:100]}")
        
        print(f"\n[SUMMARY] Synced: {synced}/{len(files_to_sync)} files")
        
        # Clear cache in vidgenerator
        print("\n[STEP 2] Clearing cache in vidgenerator...")
        stdin, stdout, stderr = ssh.exec_command("find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true")
        stdin, stdout, stderr = ssh.exec_command("find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true")
        print("  [OK] Cache cleared")
        
        # Restart uWSGI
        print("\n[STEP 3] Restarting uWSGI...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart uwsgi")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("  [OK] uWSGI restarted")
        time.sleep(8)
        
        # Test endpoints
        print("\n[STEP 4] Testing endpoints...")
        endpoints = [
            ("/vidgenerator/api/ultra-resource/energy?user_id=test", "Ultra Resource"),
            ("/vidgenerator/api/game-mechanics/subjects?user_id=test", "Game Mechanics"),
        ]
        
        for endpoint, name in endpoints:
            print(f"\n  [TEST] {name}")
            cmd = f"curl -s -w '\\nHTTP_CODE:%{{http_code}}' 'https://masternoder.dk{endpoint}'"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode('utf-8', errors='ignore')
            
            if "HTTP_CODE:200" in output:
                body = output.split("HTTP_CODE")[0].strip()
                print(f"    [SUCCESS] Status 200")
                if body and len(body) > 10:
                    print(f"    Response: {body[:150]}")
            elif "HTTP_CODE:404" in output:
                print(f"    [FAIL] Status 404")
            else:
                print(f"    [INFO] {output[:200]}")
        
        # Check debug routes
        print("\n[STEP 5] Checking debug routes...")
        stdin, stdout, stderr = ssh.exec_command("curl -s 'https://masternoder.dk/vidgenerator/api/debug/routes' | python3 -c \"import sys, json; data=json.load(sys.stdin); gm=[r for r in data.get('routes', []) if 'game-mechanics' in str(r).lower()]; print(f'Game Mechanics routes: {len(gm)}')\" 2>&1")
        debug_check = stdout.read().decode('utf-8', errors='ignore')
        print(f"  {debug_check}")
        
        ssh.close()
        
        print("\n" + "="*60)
        print("DEPLOYMENT COMPLETE")
        print("="*60)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_to_vidgenerator()


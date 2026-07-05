"""
Force Complete uWSGI Reload
Kill all processes, clear cache, restart fresh
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def force_reload():
    """Force complete uWSGI reload"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*60)
        print("FORCING COMPLETE uWSGI RELOAD")
        print("="*60)
        
        # Step 1: Stop uWSGI
        print("\n[STEP 1] Stopping uWSGI...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl stop uwsgi")
        stdout.channel.recv_exit_status()
        print("  [OK] uWSGI stopped")
        time.sleep(2)
        
        # Step 2: Kill any remaining uWSGI processes
        print("\n[STEP 2] Killing any remaining uWSGI processes...")
        stdin, stdout, stderr = ssh.exec_command("sudo pkill -9 uwsgi 2>&1 || echo 'No processes to kill'")
        kill_output = stdout.read().decode('utf-8', errors='ignore')
        print(f"  {kill_output.strip()}")
        time.sleep(3)
        
        # Step 3: Clear all Python cache
        print("\n[STEP 3] Clearing all Python cache...")
        commands = [
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyo' -delete 2>/dev/null || true",
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("  [OK] Cache cleared")
        
        # Step 4: Verify no uWSGI processes running
        print("\n[STEP 4] Verifying no uWSGI processes...")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep uwsgi | grep -v grep | wc -l")
        process_count = stdout.read().decode().strip()
        if process_count == '0':
            print("  [OK] No uWSGI processes running")
        else:
            print(f"  [WARN] {process_count} uWSGI processes still running")
        
        # Step 5: Start uWSGI fresh
        print("\n[STEP 5] Starting uWSGI fresh...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl start uwsgi")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("  [OK] uWSGI started")
        else:
            error = stderr.read().decode()
            print(f"  [ERROR] Failed to start: {error[:200]}")
        
        # Step 6: Wait for initialization
        print("\n[STEP 6] Waiting for app initialization...")
        time.sleep(15)
        
        # Step 7: Verify services are running
        print("\n[STEP 7] Verifying services...")
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi")
        status = stdout.read().decode().strip()
        if status == "active":
            print("  [OK] uWSGI is active")
        else:
            print(f"  [WARN] uWSGI status: {status}")
        
        # Step 8: Test endpoints
        print("\n[STEP 8] Testing endpoints...")
        endpoints = [
            ("/vidgenerator/api/game-mechanics/subjects?user_id=test", "Game Mechanics"),
            ("/vidgenerator/api/ultra-resource/energy?user_id=test", "Ultra Resource"),
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
        
        # Step 9: Check debug routes
        print("\n[STEP 9] Checking debug routes...")
        stdin, stdout, stderr = ssh.exec_command("curl -s 'https://masternoder.dk/vidgenerator/api/debug/routes' | python3 -c \"import sys, json; data=json.load(sys.stdin); gm=[r for r in data.get('routes', []) if 'game-mechanics' in str(r).lower()]; ur=[r for r in data.get('routes', []) if 'ultra-resource' in str(r).lower()]; print(f'Game Mechanics: {len(gm)}, Ultra Resource: {len(ur)}')\" 2>&1")
        debug_check = stdout.read().decode('utf-8', errors='ignore')
        print(f"  {debug_check}")
        
        ssh.close()
        
        print("\n" + "="*60)
        print("COMPLETE RELOAD FINISHED")
        print("="*60)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    force_reload()


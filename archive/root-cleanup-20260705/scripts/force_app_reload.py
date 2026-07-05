"""
Force Flask App Reload
Touch WSGI file and restart services to force reload
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def force_reload():
    """Force Flask app to reload"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*60)
        print("FORCING FLASK APP RELOAD")
        print("="*60)
        
        # Find and touch WSGI file
        print("\n[STEP 1] Finding and touching WSGI file...")
        wsgi_files = [
            "/var/www/html/wsgi.py",
            "/var/www/html/src/app.py",
            "/var/www/html/src/wsgi.py"
        ]
        
        for wsgi_file in wsgi_files:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {wsgi_file} && touch {wsgi_file} && echo 'TOUCHED' || echo 'NOT_FOUND'")
            result = stdout.read().decode().strip()
            if result == "TOUCHED":
                print(f"  [OK] Touched {wsgi_file}")
        
        # Restart uWSGI
        print("\n[STEP 2] Restarting uWSGI...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart uwsgi")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("  [OK] uWSGI restarted")
        time.sleep(5)
        
        # Restart python-proxy
        print("\n[STEP 3] Restarting python-proxy...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart python-proxy")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("  [OK] python-proxy restarted")
        time.sleep(5)
        
        # Wait for services to be ready
        print("\n[STEP 4] Waiting for services to initialize...")
        time.sleep(8)
        
        # Test endpoints
        print("\n[STEP 5] Testing endpoints...")
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
        
        ssh.close()
        
        print("\n" + "="*60)
        print("RELOAD COMPLETE")
        print("="*60)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    force_reload()


"""
Reload Application and Test
Touch WSGI file to trigger reload, then test endpoints
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def reload_and_test():
    """Reload app and test"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*60)
        print("RELOADING APPLICATION AND TESTING")
        print("="*60)
        
        # Find and touch WSGI file to trigger reload
        print("\n[RELOAD] Triggering application reload...")
        wsgi_files = [
            "/var/www/html/wsgi.py",
            "/var/www/html/src/app.py",
            "/var/www/html/src/wsgi.py"
        ]
        
        for wsgi_file in wsgi_files:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {wsgi_file} && touch {wsgi_file} && echo 'TOUCHED' || echo 'NOT_FOUND'")
            result = stdout.read().decode().strip()
            if result == "TOUCHED":
                print(f"[OK] Touched {wsgi_file}")
                break
        
        # Also restart uWSGI to ensure reload
        print("\n[RESTART] Restarting uWSGI...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart uwsgi")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("[OK] uWSGI restarted")
        time.sleep(5)
        
        # Test endpoints
        print("\n[TEST] Testing endpoints...")
        endpoints = [
            ("/vidgenerator/api/ultra-resource/energy?user_id=test", "Ultra Resource Controller"),
            ("/vidgenerator/api/game-mechanics/subjects?user_id=test", "Game Mechanics"),
        ]
        
        for endpoint, name in endpoints:
            print(f"\n[TEST] {name}")
            cmd = f"curl -s -w '\\nHTTP_CODE:%{{http_code}}' 'https://masternoder.dk{endpoint}'"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode()
            
            if "HTTP_CODE:200" in output:
                print(f"[OK] Status 200 - Working!")
                body = output.split("HTTP_CODE")[0].strip()
                print(f"Response: {body[:150]}...")
            elif "HTTP_CODE:404" in output:
                print(f"[FAIL] Status 404 - Not found")
            else:
                print(f"[INFO] Response: {output[:200]}")
        
        ssh.close()
        
        print("\n" + "="*60)
        print("RELOAD AND TEST COMPLETE")
        print("="*60)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reload_and_test()


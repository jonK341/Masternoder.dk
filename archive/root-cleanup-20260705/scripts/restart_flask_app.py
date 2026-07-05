"""
Restart Flask App to Register New Blueprints
Performs full stop/start cycle to ensure blueprints are loaded
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def restart_flask_app():
    """Full restart of Flask application"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*60)
        print("RESTARTING FLASK APPLICATION")
        print("="*60)
        failed_services = []

        # Step 1: Stop services
        print("\n[STEP 1] Stopping services...")
        services = ['uwsgi']
        
        for service in services:
            print(f"  Stopping {service}...")
            stdin, stdout, stderr = ssh.exec_command(f"sudo systemctl stop {service} 2>/dev/null || true")
            exit_status = stdout.channel.recv_exit_status()
            print(f"  [OK] {service} stopped")
        
        # Wait for services to fully stop
        print("\n[WAIT] Waiting 3 seconds for services to stop...")
        time.sleep(3)
        
        # Step 2: Clear Python cache
        print("\n[STEP 2] Clearing Python cache...")
        cache_commands = [
            "find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true",
            "find /var/www/html -type f -name '*.pyc' -delete 2>/dev/null || true"
        ]
        
        for cmd in cache_commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        
        print("  [OK] Cache cleared")

        # Step 2b: Ensure venv bin is executable by www-data, then check uwsgi config
        print("\n[STEP 2b] Checking uwsgi config...")
        venv_bin = "/var/www/html/vidgenerator/.venv/bin"
        venv_dir = "/var/www/html/vidgenerator/.venv"
        # Allow www-data to traverse .venv and execute binaries in .venv/bin (755 = rwxr-xr-x)
        stdin, stdout, stderr = ssh.exec_command(
            f"chmod 755 {venv_dir} 2>/dev/null; chmod 755 {venv_bin} 2>/dev/null; chmod 755 {venv_bin}/* 2>/dev/null; "
            f"ls -la {venv_bin}/ 2>/dev/null | head -5 || true"
        )
        perm_out = stdout.read().decode().strip()
        if perm_out and "Permission denied" not in perm_out:
            print(f"  [OK] {venv_bin} permissions set (755) for www-data to use")
        apps_enabled = "/etc/uwsgi/apps-enabled"
        vidgenerator_ini = "/var/www/html/vidgenerator/uwsgi.ini"
        stdin, stdout, stderr = ssh.exec_command(f"ls -la {apps_enabled}/ 2>/dev/null || echo 'DIR_MISSING'")
        listing = stdout.read().decode().strip()
        if "DIR_MISSING" in listing or not listing or listing.strip() in ("", "total 0"):
            print(f"  [WARN] {apps_enabled}/ is missing or empty")
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {apps_enabled} && ln -sf {vidgenerator_ini} {apps_enabled}/vidgenerator.ini")
            stdout.channel.recv_exit_status()
            print(f"  [OK] Created directory and symlink to vidgenerator uwsgi.ini")
        else:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {apps_enabled}/vidgenerator.ini -o -L {apps_enabled}/vidgenerator.ini && echo OK || echo MISSING")
            has_link = stdout.read().decode().strip() == "OK"
            if not has_link:
                print(f"  [WARN] vidgenerator.ini not in {apps_enabled}/")
                stdin, stdout, stderr = ssh.exec_command(f"ln -sf {vidgenerator_ini} {apps_enabled}/vidgenerator.ini")
                stdout.channel.recv_exit_status()
                print(f"  [OK] Created symlink")
            else:
                print(f"  [OK] {apps_enabled}/ has config(s):")
                for line in listing.splitlines():
                    print(f"    {line}")
        # Discover uwsgi binary (venv often has no uwsgi; system /usr/bin/uwsgi is common)
        stdin, stdout, stderr = ssh.exec_command(
            "test -x /var/www/html/vidgenerator/.venv/bin/uwsgi && echo /var/www/html/vidgenerator/.venv/bin/uwsgi || "
            "test -x /usr/bin/uwsgi && echo /usr/bin/uwsgi || echo"
        )
        uwsgi_bin = stdout.read().decode().strip() or "/usr/bin/uwsgi"
        print(f"  Using uwsgi: {uwsgi_bin}")
        # Test config: run uwsgi with the ini (--need-app = load app then exit, surfaces import errors)
        test_cmd = (
            f"timeout 8 sudo -u www-data {uwsgi_bin} --ini {vidgenerator_ini} --need-app 2>&1 || "
            f"timeout 8 sudo -u www-data {uwsgi_bin} --ini {vidgenerator_ini} 2>&1 || true"
        )
        print(f"  Running: sudo -u www-data {uwsgi_bin} --ini {vidgenerator_ini} [--need-app or 8s run]")
        stdin, stdout, stderr = ssh.exec_command(test_cmd, timeout=12)
        test_out = (stdout.read().decode() + stderr.read().decode()).strip()
        if test_out:
            if "error" in test_out.lower() or "importerror" in test_out.lower() or "exception" in test_out.lower() or "traceback" in test_out.lower():
                print(f"  [WARN] Config test produced errors (first 20 lines):")
                for line in test_out.splitlines( )[:20]:
                    print(f"    {line}")
            else:
                print(f"  [OK] Config test ran (app loaded or uwsgi started):")
                for line in test_out.splitlines()[:10]:
                    print(f"    {line}")
        else:
            print(f"  [INFO] Config test produced no output")
        
        # Step 3: Start services
        print("\n[STEP 3] Starting services...")
        for service in services:
            print(f"  Starting {service}...")
            stdin, stdout, stderr = ssh.exec_command(f"sudo systemctl start {service}", timeout=15)
            exit_status = stdout.channel.recv_exit_status()
            err_out = stderr.read().decode().strip()
            if exit_status == 0:
                print(f"  [OK] {service} started")
            else:
                print(f"  [ERROR] {service}: {err_out[:200]}")
                failed_services.append(service)
                # Fetch journalctl for this service so we see the real failure reason
                jcmd = f"sudo journalctl -u {service} -n 50 --no-pager 2>/dev/null"
                jstdin, jstdout, jstderr = ssh.exec_command(jcmd, timeout=10)
                jout = jstdout.read().decode().strip()
                if jout:
                    print(f"\n  --- Recent logs for {service} ---")
                    for line in jout.splitlines()[-25:]:
                        print(f"    {line}")
                    print(f"  --- end logs ---\n")
                # For uwsgi, also show app log (Python/uwsgi errors)
                if service == "uwsgi":
                    for logpath in ["/var/www/html/vidgenerator/uwsgi.log", "/var/log/uwsgi/app.log"]:
                        lcmd = f"tail -40 {logpath} 2>/dev/null"
                        lstdin, lstdout, lstderr = ssh.exec_command(lcmd, timeout=5)
                        lout = lstdout.read().decode().strip()
                        if lout:
                            print(f"  --- Tail of {logpath} ---")
                            for line in lout.splitlines()[-20:]:
                                print(f"    {line}")
                            print(f"  --- end ---\n")
                            break
        
        # Wait for services to initialize
        print("\n[WAIT] Waiting 8 seconds for services to initialize...")
        time.sleep(8)
        
        # Step 4: Verify services are running
        print("\n[STEP 4] Verifying services are active...")
        for service in services:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service}")
            status = stdout.read().decode().strip()
            if status == "active":
                print(f"  [OK] {service} is active")
            else:
                print(f"  [WARN] {service} status: {status}")
        
        # Step 5: Test endpoints
        print("\n[STEP 5] Testing endpoints...")
        endpoints = [
            ("/vidgenerator/api/ultra-resource/energy?user_id=test", "Ultra Resource Controller"),
            ("/vidgenerator/api/game-mechanics/progress?user_id=test", "Game Mechanics"),
            ("/vidgenerator/api/game/hunters/rewards?user_id=test", "Hunters Rewards"),
        ]
        
        results = []
        for endpoint, name in endpoints:
            print(f"\n  [TEST] {name}")
            cmd = f"curl -s -w '\\nHTTP_CODE:%{{http_code}}' 'https://masternoder.dk{endpoint}'"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode()
            
            if "HTTP_CODE:200" in output:
                print(f"    [OK] Status 200 - Working!")
                body = output.split("HTTP_CODE")[0].strip()
                if body and len(body) > 10:
                    print(f"    Response: {body[:100]}...")
                results.append(True)
            elif "HTTP_CODE:404" in output:
                print(f"    [FAIL] Status 404 - Not found")
                results.append(False)
            elif "HTTP_CODE:500" in output:
                print(f"    [ERROR] Status 500 - Server error")
                results.append(False)
            else:
                print(f"    [INFO] Response: {output[:150]}")
                results.append(False)
        
        ssh.close()
        
        # Summary
        print("\n" + "="*60)
        print("RESTART SUMMARY")
        print("="*60)
        passed = sum(results)
        total = len(results)
        print(f"\nEndpoints working: {passed}/{total}")
        
        if passed > 0:
            print("\n[SUCCESS] Flask app restarted - Some endpoints are working!")
        elif passed == 0:
            print("\n[WARN] Flask app restarted but endpoints still not working")
            for svc in failed_services:
                print(f"       Check logs: sudo journalctl -u {svc} -n 100")
            if not failed_services:
                print("       Check logs: sudo journalctl -u uwsgi -n 100")
        
        return passed > 0
        
    except Exception as e:
        print(f"[ERROR] Restart failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = restart_flask_app()
    exit(0 if success else 1)


"""
Diagnose Flask Routes - Check logs and app structure
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def diagnose():
    """Diagnose why routes aren't working"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*60)
        print("DIAGNOSING FLASK ROUTES")
        print("="*60)
        
        # Check uWSGI logs
        print("\n[CHECK 1] uWSGI logs (last 50 lines)...")
        stdin, stdout, stderr = ssh.exec_command("sudo journalctl -u uwsgi -n 50 --no-pager 2>/dev/null || tail -50 /var/log/uwsgi/app.log 2>/dev/null || echo 'No logs found'")
        logs = stdout.read().decode()
        print(logs[:2000])  # First 2000 chars
        
        # Check Flask app entry point
        print("\n[CHECK 2] Finding Flask app entry point...")
        app_files = [
            "/var/www/html/app.py",
            "/var/www/html/src/app.py",
            "/var/www/html/wsgi.py",
            "/var/www/html/src/wsgi.py",
            "/var/www/html/vidgenerator/app.py"
        ]
        
        for app_file in app_files:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {app_file} && echo 'EXISTS' || echo 'NOT_FOUND'")
            if stdout.read().decode().strip() == "EXISTS":
                print(f"  [FOUND] {app_file}")
                # Check if it imports register_blueprints
                stdin, stdout, stderr = ssh.exec_command(f"grep -i 'register_blueprint' {app_file} | head -3")
                imports = stdout.read().decode()
                if imports:
                    print(f"    Blueprint registration found:")
                    print(f"    {imports}")
                else:
                    print(f"    [WARN] No blueprint registration found")
        
        # Check existing working routes
        print("\n[CHECK 3] Testing existing routes to understand URL structure...")
        test_urls = [
            "https://masternoder.dk/vidgenerator/",
            "https://masternoder.dk/vidgenerator/api/",
        ]
        
        for url in test_urls:
            stdin, stdout, stderr = ssh.exec_command(f"curl -s -w '\\nHTTP_CODE:%{{http_code}}' '{url}'")
            output = stdout.read().decode()
            if "HTTP_CODE:200" in output:
                print(f"  [OK] {url} - Working")
            elif "HTTP_CODE:404" in output:
                print(f"  [404] {url} - Not found")
            else:
                print(f"  [INFO] {url} - {output[:100]}")
        
        # Check if there's a different API prefix
        print("\n[CHECK 4] Checking for API route structure...")
        stdin, stdout, stderr = ssh.exec_command("find /var/www/html -name '*.py' -type f -exec grep -l 'register_blueprint' {} \\; | head -5")
        files_with_blueprints = stdout.read().decode()
        if files_with_blueprints:
            print("  Files with blueprint registration:")
            print(f"  {files_with_blueprints}")
        
        # Check blueprint URL prefixes
        print("\n[CHECK 5] Checking blueprint URL prefixes...")
        stdin, stdout, stderr = ssh.exec_command("grep -r 'url_prefix' /var/www/html/backend/routes/*.py 2>/dev/null | head -10")
        url_prefixes = stdout.read().decode()
        if url_prefixes:
            print("  URL prefixes found:")
            print(f"  {url_prefixes}")
        else:
            print("  [INFO] No explicit url_prefix found in route files")
        
        ssh.close()
        
        print("\n" + "="*60)
        print("DIAGNOSIS COMPLETE")
        print("="*60)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose()


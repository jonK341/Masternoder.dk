#!/usr/bin/env python3
"""
Final fix for errno 11 error and redeploy all files
"""
import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

# All files to deploy
FILES_TO_DEPLOY = [
    ("wsgi.py", f"{REMOTE_PATH}/wsgi.py"),
    ("src/app.py", f"{REMOTE_PATH}/src/app.py"),
    ("backend/register_blueprints.py", f"{REMOTE_PATH}/backend/register_blueprints.py"),
    ("backend/routes/all_page_routes.py", f"{REMOTE_PATH}/backend/routes/all_page_routes.py"),
    ("backend/routes/dashboard_page.py", f"{REMOTE_PATH}/backend/routes/dashboard_page.py"),
    ("backend/routes/url_checker_routes.py", f"{REMOTE_PATH}/backend/routes/url_checker_routes.py"),
    ("backend/routes/debugger_download.py", f"{REMOTE_PATH}/backend/routes/debugger_download.py"),
    ("backend/routes/unified_points.py", f"{REMOTE_PATH}/backend/routes/unified_points.py"),
    ("src/web/routes.py", f"{REMOTE_PATH}/src/web/routes.py"),
    ("index.html", f"{REMOTE_PATH}/index.html"),
    ("vidgenerator/index.html", f"{REMOTE_PATH}/vidgenerator/index.html"),
    ("vidgenerator/debugger/index.html", f"{REMOTE_PATH}/vidgenerator/debugger/index.html"),
    ("vidgenerator/dashboard/index.html", f"{REMOTE_PATH}/vidgenerator/dashboard/index.html"),
    ("vidgenerator/generator/index.html", f"{REMOTE_PATH}/vidgenerator/generator/index.html"),
    ("vidgenerator/static/js/unified-point-counters.js", f"{REMOTE_PATH}/vidgenerator/static/js/unified-point-counters.js"),
    ("vidgenerator/static/js/progression-display.js", f"{REMOTE_PATH}/vidgenerator/static/js/progression-display.js"),
    ("vidgenerator/static/js/navigation-toolbar.js", f"{REMOTE_PATH}/vidgenerator/static/js/navigation-toolbar.js"),
    ("vidgenerator/static/css/modern-design-system.css", f"{REMOTE_PATH}/vidgenerator/static/css/modern-design-system.css"),
    ("vidgenerator/static/css/navigation-toolbar.css", f"{REMOTE_PATH}/vidgenerator/static/css/navigation-toolbar.css"),
]

def deploy_files(ssh_client):
    """Deploy all files"""
    print("=" * 70)
    print("DEPLOYING ALL FILES")
    print("=" * 70)
    
    sftp = ssh_client.open_sftp()
    deployed = 0
    errors = []
    
    for local_file, remote_file in FILES_TO_DEPLOY:
        if not os.path.exists(local_file):
            print(f"[SKIP] {local_file} - Not found")
            continue
        
        try:
            remote_dir = os.path.dirname(remote_file)
            ssh_client.exec_command(f"mkdir -p {remote_dir}")
            
            print(f"[{deployed + 1}/{len([f for f, _ in FILES_TO_DEPLOY if os.path.exists(f)])}] {local_file}")
            sftp.put(local_file, remote_file)
            print(f"  ✅ Deployed")
            deployed += 1
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            errors.append(f"{local_file}: {str(e)}")
    
    sftp.close()
    return deployed, errors

def verify_errno11_fix(ssh_client):
    """Verify errno 11 fix is in wsgi.py"""
    print("\n" + "=" * 70)
    print("VERIFYING ERRNO 11 FIX")
    print("=" * 70)
    
    try:
        stdin, stdout, stderr = ssh_client.exec_command(f"grep -c 'BlockingIOError\\|errno.*11' {REMOTE_PATH}/wsgi.py 2>/dev/null || echo '0'")
        count = stdout.read().decode().strip()
        if count.isdigit() and int(count) > 0:
            print(f"✅ wsgi.py has BlockingIOError handling ({count} occurrences)")
            
            # Show the relevant lines
            stdin, stdout, stderr = ssh_client.exec_command(f"grep -A 5 'BlockingIOError' {REMOTE_PATH}/wsgi.py 2>/dev/null | head -10")
            lines = stdout.read().decode().strip()
            if lines:
                print("\nRelevant code:")
                for line in lines.split('\n')[:10]:
                    print(f"  {line}")
            return True
        else:
            print(f"❌ wsgi.py missing BlockingIOError handling")
            return False
    except Exception as e:
        print(f"⚠️  Could not verify: {str(e)}")
        return False

def test_application(ssh_client):
    """Test application startup"""
    print("\n" + "=" * 70)
    print("TESTING APPLICATION STARTUP")
    print("=" * 70)
    
    # Write test script to server
    test_script = f"{REMOTE_PATH}/test_app_startup.py"
    test_code = """import sys
sys.path.insert(0, '/var/www/html/vidgenerator')
try:
    from src.app import create_app
    app = create_app()
    if app:
        print("SUCCESS: Application created")
        print(f"Blueprints: {len(app.blueprints)}")
    else:
        print("FAIL: Application is None")
except BlockingIOError as e:
    if hasattr(e, 'errno') and e.errno == 11:
        print(f"ERRNO11: {e}")
    else:
        print(f"BlockingIOError: {e}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
"""
    
    try:
        # Write test script
        sftp = ssh_client.open_sftp()
        with sftp.file(test_script, 'w') as f:
            f.write(test_code)
        sftp.close()
        
        # Run test script
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {REMOTE_PATH} && python3 {test_script} 2>&1")
        output = stdout.read().decode('utf-8', errors='ignore')
        error_output = stderr.read().decode('utf-8', errors='ignore')
        
        print(output)
        if error_output:
            print("\nSTDERR:")
            print(error_output)
        
        # Cleanup
        ssh_client.exec_command(f"rm -f {test_script}")
        
        if "SUCCESS" in output:
            return True
        elif "ERRNO11" in output:
            return False
        else:
            return None
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return None

def restart_services(ssh_client):
    """Restart services"""
    print("\n" + "=" * 70)
    print("RESTARTING SERVICES")
    print("=" * 70)
    
    restarted = []
    for service in ['uwsgi', 'python-proxy']:
        try:
            stdin, stdout, stderr = ssh_client.exec_command(f"systemctl restart {service}")
            if stdout.channel.recv_exit_status() == 0:
                print(f"✅ {service} restarted")
                restarted.append(service)
        except:
            pass
    
    # Touch files
    for f in [f"{REMOTE_PATH}/wsgi.py", f"{REMOTE_PATH}/src/app.py"]:
        try:
            ssh_client.exec_command(f"touch {f}")
        except:
            pass
    
    return restarted

def main():
    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        print("=" * 70)
        print("FINAL FIX AND REDEPLOY")
        print("=" * 70)
        print()
        
        # Deploy files
        deployed, errors = deploy_files(ssh_client)
        
        # Verify fix
        fix_verified = verify_errno11_fix(ssh_client)
        
        # Test application
        test_result = test_application(ssh_client)
        
        # Restart services
        restarted = restart_services(ssh_client)
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Files deployed: {deployed}")
        print(f"Errors: {len(errors)}")
        print(f"Errno 11 fix verified: {'✅ YES' if fix_verified else '❌ NO'}")
        print(f"Application test: {'✅ PASS' if test_result else '❌ FAIL' if test_result is False else '⚠️  UNKNOWN'}")
        print(f"Services restarted: {len(restarted)}")
        
        if errors:
            print(f"\n❌ Errors:")
            for e in errors:
                print(f"  - {e}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()


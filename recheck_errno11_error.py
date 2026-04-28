#!/usr/bin/env python3
"""
Recheck errno 11 error - verify fix is working
"""
import os
import sys
import paramiko
import time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

def check_recent_errors(ssh_client):
    """Check for recent errno 11 errors in logs"""
    print("=" * 70)
    print("CHECKING FOR RECENT ERRNO 11 ERRORS")
    print("=" * 70)
    
    # Get current timestamp
    now = datetime.now()
    cutoff_time = now.timestamp() - 300  # Last 5 minutes
    
    # Check wsgi_error.log
    print("\n1. Checking wsgi_error.log...")
    try:
        # Get file modification time and last 100 lines
        stdin, stdout, stderr = ssh_client.exec_command(f"stat -c %Y {REMOTE_PATH}/logs/wsgi_error.log 2>/dev/null && tail -n 100 {REMOTE_PATH}/logs/wsgi_error.log 2>/dev/null")
        output = stdout.read().decode('utf-8', errors='ignore')
        lines = output.split('\n')
        
        # First line is timestamp
        if lines and lines[0].isdigit():
            file_mtime = int(lines[0])
            log_lines = lines[1:]
            
            # Check if file was modified recently (within last 5 minutes)
            if file_mtime > cutoff_time:
                print(f"⚠️  Log file modified recently (within last 5 minutes)")
            else:
                print(f"✅ Log file not modified recently (last modified: {datetime.fromtimestamp(file_mtime)})")
            
            # Check for errno 11 errors
            errno11_count = 0
            recent_errno11 = []
            for line in log_lines:
                if 'errno.*11' in line.lower() or '[errno 11]' in line.lower() or 'write could not complete' in line.lower():
                    errno11_count += 1
                    recent_errno11.append(line)
            
            if errno11_count > 0:
                print(f"⚠️  Found {errno11_count} errno 11 error(s) in log")
                print("Recent errors:")
                for line in recent_errno11[-5:]:  # Last 5
                    print(f"  {line[:100]}")
            else:
                print("✅ No errno 11 errors found in recent log entries")
        else:
            print("⚠️  Could not read log file")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    # Check uWSGI logs
    print("\n2. Checking uWSGI systemd logs...")
    try:
        stdin, stdout, stderr = ssh_client.exec_command("journalctl -u uwsgi --since '5 minutes ago' --no-pager | grep -i 'errno.*11\\|blocking\\|write could not' || echo 'No errno 11 errors in uWSGI logs'")
        output = stdout.read().decode('utf-8', errors='ignore')
        if output.strip() and 'No errno 11' not in output:
            print("⚠️  Found errno 11 errors in uWSGI logs:")
            print(output[:500])
        else:
            print("✅ No errno 11 errors in uWSGI logs (last 5 minutes)")
    except Exception as e:
        print(f"Error: {str(e)}")

def verify_wsgi_fix(ssh_client):
    """Verify wsgi.py has the correct fix"""
    print("\n" + "=" * 70)
    print("VERIFYING WSGI.PY FIX")
    print("=" * 70)
    
    try:
        # Check if output suppression is BEFORE create_app
        stdin, stdout, stderr = ssh_client.exec_command(f"grep -A 10 'SUPPRESS ALL OUTPUT' {REMOTE_PATH}/wsgi.py | head -15")
        fix_code = stdout.read().decode('utf-8', errors='ignore')
        
        if 'SUPPRESS ALL OUTPUT' in fix_code and 'contextlib.redirect_stdout' in fix_code:
            print("✅ Fix is present:")
            for line in fix_code.split('\n')[:12]:
                if line.strip():
                    print(f"  {line}")
            
            # Verify the order: redirect should be BEFORE create_app
            stdin, stdout, stderr = ssh_client.exec_command(f"grep -n 'redirect_stdout\\|create_app' {REMOTE_PATH}/wsgi.py | head -5")
            order = stdout.read().decode('utf-8', errors='ignore')
            if order:
                print("\nOrder check:")
                for line in order.split('\n')[:5]:
                    if line.strip():
                        print(f"  {line}")
                
                # Check if redirect comes before create_app
                lines = order.split('\n')
                redirect_line = None
                create_app_line = None
                for line in lines:
                    if 'redirect_stdout' in line and redirect_line is None:
                        redirect_line = int(line.split(':')[0])
                    if 'create_app()' in line and create_app_line is None:
                        create_app_line = int(line.split(':')[0])
                
                if redirect_line and create_app_line:
                    if redirect_line < create_app_line:
                        print(f"\n✅ Correct order: redirect_stdout (line {redirect_line}) comes before create_app() (line {create_app_line})")
                    else:
                        print(f"\n❌ Wrong order: redirect_stdout (line {redirect_line}) comes after create_app() (line {create_app_line})")
        else:
            print("❌ Fix not found in wsgi.py")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_application_startup(ssh_client):
    """Test application startup to see if errno 11 occurs"""
    print("\n" + "=" * 70)
    print("TESTING APPLICATION STARTUP")
    print("=" * 70)
    
    test_script = f"{REMOTE_PATH}/test_errno11_recheck.py"
    test_code = """import sys
import os
import traceback
from datetime import datetime

print(f"Test started at {datetime.now()}")
print("STEP 1: Importing create_app...")

try:
    sys.path.insert(0, '/var/www/html/vidgenerator')
    from src.app import create_app
    print("STEP 2: Calling create_app()...")
    
    # Test with output suppression (like wsgi.py does)
    import contextlib
    with open(os.devnull, 'w') as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            app = create_app()
    
    if app:
        print("SUCCESS: Application created without errno 11 error")
        print(f"Blueprints: {len(app.blueprints)}")
    else:
        print("FAIL: Application is None")
        
except BlockingIOError as e:
    errno = getattr(e, 'errno', None)
    if errno == 11:
        print(f"ERRNO11_ERROR: {e}")
        traceback.print_exc()
    else:
        print(f"BlockingIOError (errno {errno}): {e}")
        traceback.print_exc()
except OSError as e:
    errno = getattr(e, 'errno', None)
    if errno == 11:
        print(f"ERRNO11_OSERROR: {e}")
        traceback.print_exc()
    else:
        print(f"OSError (errno {errno}): {e}")
        traceback.print_exc()
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    traceback.print_exc()

print(f"Test completed at {datetime.now()}")
"""
    
    try:
        sftp = ssh_client.open_sftp()
        with sftp.file(test_script, 'w') as f:
            f.write(test_code)
        sftp.close()
        
        print("Running test script...")
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {REMOTE_PATH} && python3 {test_script} 2>&1")
        output = stdout.read().decode('utf-8', errors='ignore')
        error_output = stderr.read().decode('utf-8', errors='ignore')
        
        print("\nSTDOUT:")
        print(output)
        if error_output:
            print("\nSTDERR:")
            print(error_output)
        
        # Cleanup
        ssh_client.exec_command(f"rm -f {test_script}")
        
        if "SUCCESS" in output and "ERRNO11" not in output:
            return True
        elif "ERRNO11" in output:
            return False
        else:
            return None
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def check_uwsgi_processes(ssh_client):
    """Check uWSGI processes and their status"""
    print("\n" + "=" * 70)
    print("CHECKING UWSGI PROCESSES")
    print("=" * 70)
    
    try:
        # Check processes
        stdin, stdout, stderr = ssh_client.exec_command("ps aux | grep uwsgi | grep -v grep")
        processes = stdout.read().decode('utf-8', errors='ignore')
        if processes:
            print("✅ uWSGI processes running:")
            for line in processes.split('\n')[:10]:
                if line.strip():
                    print(f"  {line}")
        else:
            print("❌ No uWSGI processes found")
        
        # Check service status
        print("\nService status:")
        stdin, stdout, stderr = ssh_client.exec_command("systemctl status uwsgi --no-pager -l | head -25")
        status = stdout.read().decode('utf-8', errors='ignore')
        print(status)
        
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        print("=" * 70)
        print("RECHECKING ERRNO 11 ERROR")
        print("=" * 70)
        print(f"Time: {datetime.now()}")
        print()
        
        # Check recent errors
        check_recent_errors(ssh_client)
        
        # Verify fix
        verify_wsgi_fix(ssh_client)
        
        # Test application startup
        test_result = test_application_startup(ssh_client)
        
        # Check uWSGI processes
        check_uwsgi_processes(ssh_client)
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Application startup test: {'✅ PASS (no errno 11)' if test_result else '❌ FAIL (errno 11 occurred)' if test_result is False else '⚠️  UNKNOWN'}")
        
        if test_result:
            print("\n✅ The fix appears to be working - no errno 11 errors during test")
        elif test_result is False:
            print("\n❌ The fix is NOT working - errno 11 errors still occurring")
        else:
            print("\n⚠️  Could not determine if fix is working")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()


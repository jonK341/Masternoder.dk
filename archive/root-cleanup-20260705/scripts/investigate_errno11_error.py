#!/usr/bin/env python3
"""
Investigate errno 11 error - check server logs and verify fixes
"""
import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

def check_uwsgi_logs(ssh_client):
    """Check uWSGI logs for errno 11 errors"""
    print("=" * 70)
    print("CHECKING UWSGI LOGS")
    print("=" * 70)
    
    log_commands = [
        ("journalctl -u uwsgi -n 100 --no-pager", "uWSGI systemd logs"),
        (f"tail -n 200 {REMOTE_PATH}/logs/app.log 2>/dev/null || echo 'No app.log'", "Application log"),
        (f"tail -n 200 {REMOTE_PATH}/logs/wsgi_error.log 2>/dev/null || echo 'No wsgi_error.log'", "WSGI error log"),
        (f"cat /var/log/uwsgi/app/vidgenerator.log 2>/dev/null | tail -n 100 || echo 'No uwsgi app log'", "uWSGI app log"),
    ]
    
    for cmd, desc in log_commands:
        try:
            print(f"\n--- {desc} ---")
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            output = stdout.read().decode('utf-8', errors='ignore')
            if output.strip():
                # Look for errno 11 errors
                lines = output.split('\n')
                errno11_lines = [l for l in lines if 'errno.*11' in l.lower() or '[errno 11]' in l.lower() or 'write could not complete' in l.lower()]
                if errno11_lines:
                    print("🔴 ERRNO 11 ERRORS FOUND:")
                    for line in errno11_lines[-10:]:  # Last 10 occurrences
                        print(f"  {line}")
                else:
                    print("✅ No errno 11 errors in recent logs")
                    # Show last 20 lines
                    for line in lines[-20:]:
                        if line.strip():
                            print(line)
            else:
                print("  (empty)")
        except Exception as e:
            print(f"  Error: {str(e)}")

def verify_wsgi_fix(ssh_client):
    """Verify wsgi.py has the fix"""
    print("\n" + "=" * 70)
    print("VERIFYING WSGI.PY FIX")
    print("=" * 70)
    
    try:
        # Check if BlockingIOError handling exists
        stdin, stdout, stderr = ssh_client.exec_command(f"grep -n 'BlockingIOError' {REMOTE_PATH}/wsgi.py")
        lines = stdout.read().decode('utf-8', errors='ignore')
        if lines:
            print("✅ BlockingIOError handling found:")
            for line in lines.split('\n')[:10]:
                if line.strip():
                    print(f"  {line}")
        else:
            print("❌ BlockingIOError handling NOT found in wsgi.py")
        
        # Check for errno 11 handling
        stdin, stdout, stderr = ssh_client.exec_command(f"grep -n 'errno.*11' {REMOTE_PATH}/wsgi.py")
        lines = stdout.read().decode('utf-8', errors='ignore')
        if lines:
            print("\n✅ errno 11 handling found:")
            for line in lines.split('\n')[:10]:
                if line.strip():
                    print(f"  {line}")
        
        # Show the relevant exception handler
        stdin, stdout, stderr = ssh_client.exec_command(f"grep -A 20 'except (BlockingIOError' {REMOTE_PATH}/wsgi.py | head -25")
        handler = stdout.read().decode('utf-8', errors='ignore')
        if handler:
            print("\nException handler code:")
            for line in handler.split('\n'):
                if line.strip():
                    print(f"  {line}")
    except Exception as e:
        print(f"Error: {str(e)}")

def check_all_print_statements(ssh_client):
    """Check for print statements that might cause blocking"""
    print("\n" + "=" * 70)
    print("CHECKING FOR PROBLEMATIC PRINT STATEMENTS")
    print("=" * 70)
    
    files_to_check = [
        f"{REMOTE_PATH}/src/app.py",
        f"{REMOTE_PATH}/backend/register_blueprints.py",
        f"{REMOTE_PATH}/wsgi.py",
    ]
    
    for file_path in files_to_check:
        try:
            # Check for print with flush=True
            stdin, stdout, stderr = ssh_client.exec_command(f"grep -n 'print.*flush=True' {file_path} 2>/dev/null")
            prints = stdout.read().decode('utf-8', errors='ignore')
            if prints.strip():
                print(f"\n⚠️  {file_path} has print(..., flush=True):")
                for line in prints.split('\n')[:10]:
                    if line.strip():
                        print(f"  {line}")
            
            # Check for print in create_app or initialization functions
            stdin, stdout, stderr = ssh_client.exec_command(f"grep -n 'def create_app\\|def register_all_blueprints' -A 50 {file_path} 2>/dev/null | grep -n 'print(' | head -20")
            init_prints = stdout.read().decode('utf-8', errors='ignore')
            if init_prints.strip():
                print(f"\n⚠️  {file_path} has print statements in initialization:")
                for line in init_prints.split('\n')[:15]:
                    if line.strip():
                        print(f"  {line}")
        except Exception as e:
            print(f"Error checking {file_path}: {str(e)}")

def check_uwsgi_status(ssh_client):
    """Check uWSGI status and process"""
    print("\n" + "=" * 70)
    print("CHECKING UWSGI STATUS")
    print("=" * 70)
    
    try:
        # Check service status
        stdin, stdout, stderr = ssh_client.exec_command("systemctl status uwsgi --no-pager -l")
        status = stdout.read().decode('utf-8', errors='ignore')
        print(status[-500:] if len(status) > 500 else status)
        
        # Check if uWSGI process is running
        stdin, stdout, stderr = ssh_client.exec_command("ps aux | grep uwsgi | grep -v grep")
        processes = stdout.read().decode('utf-8', errors='ignore')
        if processes:
            print("\n✅ uWSGI processes running:")
            for line in processes.split('\n')[:5]:
                if line.strip():
                    print(f"  {line}")
        else:
            print("\n❌ No uWSGI processes found")
    except Exception as e:
        print(f"Error: {str(e)}")

def test_app_creation_with_full_output(ssh_client):
    """Test app creation and capture full error output"""
    print("\n" + "=" * 70)
    print("TESTING APPLICATION CREATION (FULL OUTPUT)")
    print("=" * 70)
    
    test_script = f"{REMOTE_PATH}/test_errno11.py"
    test_code = """import sys
import os
import traceback

# Redirect stderr to capture all errors
original_stderr = sys.stderr
error_log = []

class ErrorCapture:
    def write(self, s):
        error_log.append(s)
        original_stderr.write(s)
    def flush(self):
        original_stderr.flush()

sys.stderr = ErrorCapture()

try:
    sys.path.insert(0, '/var/www/html/vidgenerator')
    print("STEP 1: Importing create_app...")
    from src.app import create_app
    print("STEP 2: Calling create_app()...")
    app = create_app()
    if app:
        print("SUCCESS: Application created")
        print(f"Blueprints: {len(app.blueprints)}")
    else:
        print("FAIL: Application is None")
except BlockingIOError as e:
    errno = getattr(e, 'errno', None)
    if errno == 11:
        print(f"ERRNO11_BLOCKING: {e}")
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

sys.stderr = original_stderr
"""
    
    try:
        sftp = ssh_client.open_sftp()
        with sftp.file(test_script, 'w') as f:
            f.write(test_code)
        sftp.close()
        
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {REMOTE_PATH} && python3 {test_script} 2>&1")
        output = stdout.read().decode('utf-8', errors='ignore')
        error_output = stderr.read().decode('utf-8', errors='ignore')
        
        print("STDOUT:")
        print(output)
        if error_output:
            print("\nSTDERR:")
            print(error_output)
        
        # Cleanup
        ssh_client.exec_command(f"rm -f {test_script}")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

def force_restart_uwsgi(ssh_client):
    """Force restart uWSGI by killing and restarting"""
    print("\n" + "=" * 70)
    print("FORCE RESTARTING UWSGI")
    print("=" * 70)
    
    try:
        # Stop uWSGI
        print("Stopping uWSGI...")
        stdin, stdout, stderr = ssh_client.exec_command("systemctl stop uwsgi")
        stdout.channel.recv_exit_status()
        print("✅ uWSGI stopped")
        
        # Kill any remaining processes
        print("Killing any remaining uWSGI processes...")
        ssh_client.exec_command("pkill -9 uwsgi")
        
        # Wait a moment
        import time
        time.sleep(2)
        
        # Start uWSGI
        print("Starting uWSGI...")
        stdin, stdout, stderr = ssh_client.exec_command("systemctl start uwsgi")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("✅ uWSGI started")
        else:
            error = stderr.read().decode('utf-8', errors='ignore')
            print(f"⚠️  uWSGI start had issues: {error[:200]}")
        
        # Check status
        stdin, stdout, stderr = ssh_client.exec_command("systemctl status uwsgi --no-pager -l | head -20")
        status = stdout.read().decode('utf-8', errors='ignore')
        print("\nStatus:")
        print(status)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        print("=" * 70)
        print("INVESTIGATING ERRNO 11 ERROR")
        print("=" * 70)
        print()
        
        # Check logs
        check_uwsgi_logs(ssh_client)
        
        # Verify fix
        verify_wsgi_fix(ssh_client)
        
        # Check print statements
        check_all_print_statements(ssh_client)
        
        # Check uWSGI status
        check_uwsgi_status(ssh_client)
        
        # Test app creation
        test_app_creation_with_full_output(ssh_client)
        
        # Ask if we should force restart
        print("\n" + "=" * 70)
        response = input("Force restart uWSGI? (yes/no): ").strip().lower()
        if response == 'yes':
            force_restart_uwsgi(ssh_client)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()


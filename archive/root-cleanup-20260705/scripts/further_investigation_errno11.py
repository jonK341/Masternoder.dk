#!/usr/bin/env python3
"""
Further investigation into errno 11 error
"""
import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

def check_uwsgi_config_file(ssh_client):
    """Check and modify uWSGI config file"""
    print("=" * 70)
    print("CHECKING UWSGI CONFIGURATION FILE")
    print("=" * 70)
    
    config_file = f"{REMOTE_PATH}/uwsgi.ini"
    
    try:
        # Read current config
        stdin, stdout, stderr = ssh_client.exec_command(f"cat {config_file}")
        content = stdout.read().decode('utf-8', errors='ignore')
        
        print("\nCurrent uWSGI configuration:")
        print(content[:1000])
        
        # Check if disable-write-exception is set
        if 'disable-write-exception' in content.lower():
            print("\n✅ disable-write-exception is already set")
        else:
            print("\n⚠️  disable-write-exception is NOT set")
            print("   This option tells uWSGI to ignore write exceptions")
        
        # Check for other relevant settings
        relevant_settings = ['buffer-size', 'post-buffering', 'logto', 'daemonize']
        found_settings = []
        for setting in relevant_settings:
            if setting in content.lower():
                found_settings.append(setting)
        
        if found_settings:
            print(f"\n✅ Found settings: {', '.join(found_settings)}")
        
        return content
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def check_uwsgi_logs_detailed(ssh_client):
    """Check uWSGI logs in detail"""
    print("\n" + "=" * 70)
    print("CHECKING UWSGI LOGS IN DETAIL")
    print("=" * 70)
    
    log_files = [
        f"{REMOTE_PATH}/uwsgi.log",
        "/var/log/uwsgi/app/vidgenerator.log",
        f"{REMOTE_PATH}/logs/wsgi_error.log",
    ]
    
    for log_file in log_files:
        print(f"\n--- {log_file} ---")
        try:
            stdin, stdout, stderr = ssh_client.exec_command(f"tail -n 100 {log_file} 2>/dev/null")
            output = stdout.read().decode('utf-8', errors='ignore')
            
            if output.strip():
                # Look for errno 11 or blocking errors
                lines = output.split('\n')
                error_lines = [l for l in lines if 'errno' in l.lower() or 'blocking' in l.lower() or 'error' in l.lower()]
                
                if error_lines:
                    print(f"⚠️  Found {len(error_lines)} error-related lines:")
                    for line in error_lines[-20:]:  # Last 20
                        print(f"  {line[:150]}")
                else:
                    print("✅ No error-related lines found")
                    # Show last 10 lines
                    for line in lines[-10:]:
                        if line.strip():
                            print(f"  {line}")
            else:
                print("  (empty or not found)")
        except Exception as e:
            print(f"  Error: {str(e)}")

def test_application_actually_works(ssh_client):
    """Test if application actually works despite error message"""
    print("\n" + "=" * 70)
    print("TESTING IF APPLICATION ACTUALLY WORKS")
    print("=" * 70)
    
    # Test with curl and capture full response
    test_urls = [
        "https://masternoder.dk/vidgenerator/",
        "https://masternoder.dk/vidgenerator/api/health",
    ]
    
    for url in test_urls:
        print(f"\nTesting: {url}")
        try:
            # Get full response (first 500 chars)
            cmd = f"curl -s -k '{url}' 2>&1 | head -c 500"
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            response = stdout.read().decode('utf-8', errors='ignore')
            
            # Get HTTP status code
            cmd2 = f"curl -s -o /dev/null -w '%{{http_code}}' -k '{url}' 2>&1"
            stdin, stdout, stderr = ssh_client.exec_command(cmd2)
            status = stdout.read().decode('utf-8', errors='ignore').strip()
            
            print(f"  Status: {status}")
            if status == '200':
                print(f"  ✅ Application is working!")
                print(f"  Response preview: {response[:200]}")
            elif status == '500':
                if 'errno.*11' in response.lower() or 'errno 11' in response.lower():
                    print(f"  ❌ Returns errno 11 error message")
                    print(f"  Response: {response[:200]}")
                else:
                    print(f"  ⚠️  Returns 500 but different error")
                    print(f"  Response: {response[:200]}")
            else:
                print(f"  Status: {status}")
                print(f"  Response: {response[:200]}")
        except Exception as e:
            print(f"  Error: {str(e)}")

def check_error_traceback(ssh_client):
    """Get full error traceback"""
    print("\n" + "=" * 70)
    print("CHECKING ERROR TRACEBACK")
    print("=" * 70)
    
    # Check wsgi_error.log for full traceback
    try:
        stdin, stdout, stderr = ssh_client.exec_command(f"tail -n 200 {REMOTE_PATH}/logs/wsgi_error.log | grep -A 30 'Traceback' | tail -40")
        traceback = stdout.read().decode('utf-8', errors='ignore')
        
        if traceback.strip():
            print("Recent traceback:")
            print(traceback)
        else:
            print("No traceback found in logs")
    except Exception as e:
        print(f"Error: {str(e)}")

def check_uwsgi_process_details(ssh_client):
    """Check uWSGI process details"""
    print("\n" + "=" * 70)
    print("CHECKING UWSGI PROCESS DETAILS")
    print("=" * 70)
    
    try:
        # Get master process
        stdin, stdout, stderr = ssh_client.exec_command("ps aux | grep 'uwsgi --ini' | grep -v grep | head -1")
        process_info = stdout.read().decode('utf-8', errors='ignore')
        
        if process_info:
            print("uWSGI master process:")
            print(process_info)
            
            # Get PID
            parts = process_info.split()
            if len(parts) >= 2:
                pid = parts[1]
                
                # Check file descriptors
                print(f"\nFile descriptors for PID {pid}:")
                stdin, stdout, stderr = ssh_client.exec_command(f"ls -la /proc/{pid}/fd/ 2>/dev/null | head -30")
                fds = stdout.read().decode('utf-8', errors='ignore')
                print(fds)
                
                # Check if stdout is a socket
                stdin, stdout, stderr = ssh_client.exec_command(f"readlink /proc/{pid}/fd/1 2>/dev/null")
                stdout_fd = stdout.read().decode('utf-8', errors='ignore').strip()
                if stdout_fd:
                    print(f"\nstdout (fd 1) points to: {stdout_fd}")
                    if 'socket' in stdout_fd:
                        print("  ⚠️  stdout is a socket (non-blocking I/O)")
    except Exception as e:
        print(f"Error: {str(e)}")

def check_if_app_creates_successfully(ssh_client):
    """Check if app creates successfully in uWSGI context"""
    print("\n" + "=" * 70)
    print("TESTING APP CREATION IN UWSGI CONTEXT")
    print("=" * 70)
    
    test_script = f"{REMOTE_PATH}/test_uwsgi_context.py"
    test_code = """import sys
import os

# Simulate uWSGI environment
# uWSGI sets stdout/stderr to non-blocking sockets

sys.path.insert(0, '/var/www/html/vidgenerator')

# Try to create app
try:
    # Monkey-patch print to ignore BlockingIOError
    import builtins
    _original_print = builtins.print
    
    def _safe_print(*args, **kwargs):
        try:
            _original_print(*args, **kwargs)
        except (BlockingIOError, OSError) as e:
            errno = getattr(e, 'errno', None)
            if errno == 11:
                pass  # Ignore
            else:
                raise
    
    builtins.print = _safe_print
    
    from src.app import create_app
    app = create_app()
    
    if app:
        print("SUCCESS: App created in simulated uWSGI context")
        print(f"Blueprints: {len(app.blueprints)}")
    else:
        print("FAIL: App is None")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
"""
    
    try:
        sftp = ssh_client.open_sftp()
        with sftp.file(test_script, 'w') as f:
            f.write(test_code)
        sftp.close()
        
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {REMOTE_PATH} && python3 {test_script} 2>&1")
        output = stdout.read().decode('utf-8', errors='ignore')
        error_output = stderr.read().decode('utf-8', errors='ignore')
        
        print("\nOutput:")
        print(output)
        if error_output:
            print("\nError:")
            print(error_output)
        
        ssh_client.exec_command(f"rm -f {test_script}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

def suggest_uwsgi_fix(ssh_client):
    """Suggest uWSGI configuration fix"""
    print("\n" + "=" * 70)
    print("SUGGESTED UWSGI CONFIGURATION FIX")
    print("=" * 70)
    
    config_file = f"{REMOTE_PATH}/uwsgi.ini"
    
    print("\nRecommended addition to uwsgi.ini:")
    print("  disable-write-exception = true")
    print("\nThis tells uWSGI to ignore write exceptions instead of propagating them.")
    print("This should prevent errno 11 errors from breaking the application.")
    
    response = input("\nAdd this setting to uwsgi.ini? (yes/no): ").strip().lower()
    if response == 'yes':
        try:
            # Read current config
            stdin, stdout, stderr = ssh_client.exec_command(f"cat {config_file}")
            content = stdout.read().decode('utf-8', errors='ignore')
            
            # Check if already has it
            if 'disable-write-exception' not in content.lower():
                # Add the setting
                new_content = content.rstrip() + "\n# Ignore write exceptions to prevent errno 11 errors\ndisable-write-exception = true\n"
                
                # Write back
                sftp = ssh_client.open_sftp()
                with sftp.file(config_file, 'w') as f:
                    f.write(new_content)
                sftp.close()
                
                print("✅ Added disable-write-exception to uwsgi.ini")
                print("⚠️  uWSGI needs to be restarted for changes to take effect")
                
                response2 = input("Restart uWSGI now? (yes/no): ").strip().lower()
                if response2 == 'yes':
                    stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi")
                    stdout.channel.recv_exit_status()
                    print("✅ uWSGI restarted")
            else:
                print("✅ disable-write-exception is already in config")
        except Exception as e:
            print(f"Error: {str(e)}")

def main():
    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        print("=" * 70)
        print("FURTHER INVESTIGATION INTO ERRNO 11 ERROR")
        print("=" * 70)
        print()
        
        # Check uWSGI config
        config_content = check_uwsgi_config_file(ssh_client)
        
        # Check logs in detail
        check_uwsgi_logs_detailed(ssh_client)
        
        # Test if app actually works
        test_application_actually_works(ssh_client)
        
        # Check error traceback
        check_error_traceback(ssh_client)
        
        # Check uWSGI process details
        check_uwsgi_process_details(ssh_client)
        
        # Test app creation
        check_if_app_creates_successfully(ssh_client)
        
        # Suggest uWSGI fix
        suggest_uwsgi_fix(ssh_client)
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()


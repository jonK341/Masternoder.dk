#!/usr/bin/env python3
"""Simple test - write script to server and run"""
import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

def main():
    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        print("=" * 70)
        print("TESTING APPLICATION CREATION")
        print("=" * 70)
        
        # Write test script
        test_script_path = f"{REMOTE_PATH}/test_app_create.py"
        script_content = """import sys
import os
sys.path.insert(0, '/var/www/html/vidgenerator')

import contextlib
_original_stdout = sys.stdout
_original_stderr = sys.stderr
try:
    _devnull = open(os.devnull, 'w')
    sys.stdout = _devnull
    sys.stderr = _devnull
except:
    pass

try:
    from src.app import create_app
    application = create_app()
    print("SUCCESS")
except SyntaxError as e:
    print("SYNTAX_ERROR")
    print(f"Line: {e.lineno}")
    print(f"File: {e.filename}")
    print(f"Msg: {e.msg}")
    if e.text:
        print(f"Text: {e.text.rstrip()}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    try:
        sys.stdout = _original_stdout
        sys.stderr = _original_stderr
        if '_devnull' in locals():
            _devnull.close()
    except:
        pass
"""
        
        sftp = ssh_client.open_sftp()
        with sftp.file(test_script_path, 'w') as f:
            f.write(script_content.encode('utf-8'))
        sftp.close()
        
        # Run it
        print("\nRunning test...")
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {REMOTE_PATH} && python3 test_app_create.py 2>&1")
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        full_output = output + error
        print(full_output)
        
        if 'SUCCESS' in full_output:
            print("\n✅ Application creation works!")
            print("The error on the web page might be from cached error or uWSGI needs restart")
            
            # Force restart uWSGI
            print("\nForce restarting uWSGI...")
            ssh_client.exec_command("systemctl stop uwsgi")
            import time
            time.sleep(2)
            ssh_client.exec_command(f"find {REMOTE_PATH} -type d -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null")
            ssh_client.exec_command(f"find {REMOTE_PATH} -name '*.pyc' -delete 2>/dev/null")
            ssh_client.exec_command("systemctl start uwsgi")
            time.sleep(5)
            print("✅ uWSGI restarted")
        elif 'SYNTAX_ERROR' in full_output:
            print("\n❌ Found syntax error!")
            # Extract line number
            for line in full_output.split('\n'):
                if 'Line:' in line:
                    try:
                        error_line = int(line.split(':', 1)[1].strip())
                        print(f"Error at line {error_line}")
                        # Fix it using the server-side script
                        print("\nRunning server-side fix...")
                        ssh_client.exec_command(f"bash {REMOTE_PATH}/fix_line_528.sh")
                    except:
                        pass
        
        # Clean up
        try:
            sftp = ssh_client.open_sftp()
            sftp.remove(test_script_path)
            sftp.close()
        except:
            pass
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()


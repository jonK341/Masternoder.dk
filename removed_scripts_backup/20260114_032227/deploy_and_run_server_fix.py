#!/usr/bin/env python3
"""Deploy and run server-side fix script"""
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
        print("DEPLOYING SERVER-SIDE FIX SCRIPT")
        print("=" * 70)
        
        # Read the server-side script
        script_path = "server_side_fix.sh"
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        # Deploy to server
        remote_script_path = f"{REMOTE_PATH}/fix_line_528.sh"
        sftp = ssh_client.open_sftp()
        with sftp.file(remote_script_path, 'w') as f:
            f.write(script_content.encode('utf-8'))
        sftp.close()
        
        # Make executable
        ssh_client.exec_command(f"chmod +x {remote_script_path}")
        
        print(f"\n✅ Script deployed to: {remote_script_path}")
        print("\nRunning server-side fix script...")
        print("=" * 70)
        
        # Run the script
        stdin, stdout, stderr = ssh_client.exec_command(f"bash {remote_script_path}")
        
        # Stream output in real-time
        import select
        import time
        
        output_lines = []
        error_lines = []
        
        # Read output
        while True:
            if stdout.channel.recv_ready():
                data = stdout.channel.recv(4096).decode('utf-8', errors='ignore')
                if data:
                    print(data, end='')
                    output_lines.append(data)
            
            if stderr.channel.recv_stderr_ready():
                data = stderr.channel.recv_stderr(4096).decode('utf-8', errors='ignore')
                if data:
                    print(data, end='', file=sys.stderr)
                    error_lines.append(data)
            
            if stdout.channel.exit_status_ready():
                break
            
            time.sleep(0.1)
        
        # Get exit status
        exit_status = stdout.channel.recv_exit_status()
        
        print("\n" + "=" * 70)
        if exit_status == 0:
            print("✅ SERVER-SIDE FIX COMPLETED SUCCESSFULLY")
        else:
            print(f"⚠️  Script exited with status {exit_status}")
        print("=" * 70)
        
        # Check for any remaining errors in uWSGI logs
        print("\nChecking uWSGI logs for line 528 errors...")
        stdin, stdout, stderr = ssh_client.exec_command("journalctl -u uwsgi --since '2 minutes ago' --no-pager | grep -i 'line 528\\|line 530\\|SyntaxError\\|IndentationError' | tail -10")
        log_output = stdout.read().decode('utf-8', errors='ignore')
        if log_output.strip():
            print("⚠️  Found errors in logs:")
            print(log_output)
        else:
            print("✅ No errors found in recent uWSGI logs")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()


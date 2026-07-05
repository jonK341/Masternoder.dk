"""
Get Flask error when accessed directly
"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def get_error():
    """Get Flask error"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("GETTING FLASK ERROR (DIRECT ACCESS)")
        print("=" * 80)
        print()
        
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        # Trigger request to Flask directly
        print("1. Triggering request to Flask directly...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("curl -v http://127.0.0.1:5000/aggregator 2>&1")
        result = stdout.read().decode('utf-8', errors='ignore')
        print(result)
        print()
        
        # Check uWSGI logs immediately after
        print("2. Checking uWSGI logs for error...")
        print("-" * 80)
        time.sleep(1)
        stdin, stdout, stderr = ssh.exec_command("tail -100 /var/log/uwsgi/app/vidgenerator.log 2>/dev/null | tail -50")
        result = stdout.read().decode('utf-8', errors='ignore')
        if result:
            # Filter for aggregator or error
            lines = result.split('\n')
            relevant = []
            for i, line in enumerate(lines):
                if 'aggregator' in line.lower() or 'error' in line.lower() or 'exception' in line.lower() or 'traceback' in line.lower():
                    relevant.append(line)
                    # Get context
                    if i > 0:
                        relevant.append(lines[i-1])
                    if i < len(lines) - 1:
                        relevant.append(lines[i+1])
            
            if relevant:
                print('\n'.join(relevant[-40:]))
            else:
                print("No relevant errors found")
                print("\nLast 30 lines:")
                print('\n'.join(lines[-30:]))
        else:
            print("No log output")
        
        # Check if Flask process is running
        print("\n3. Checking Flask/uWSGI process...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep -E 'uwsgi|flask|python.*5000' | grep -v grep")
        result = stdout.read().decode('utf-8', errors='ignore')
        print(result if result else "No process found")
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()

if __name__ == '__main__':
    get_error()


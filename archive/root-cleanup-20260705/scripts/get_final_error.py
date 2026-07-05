"""
Get the final error from server after request
"""
import paramiko
import os
import sys
import time
import requests

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def get_error():
    """Get error from server"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("GETTING FINAL ERROR FROM SERVER")
        print("=" * 80)
        print()
        
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        # Trigger request
        print("Triggering request...")
        try:
            requests.get("https://masternoder.dk/vidgenerator/aggregator", timeout=5)
        except:
            pass
        time.sleep(3)
        
        # Get the absolute latest logs
        print("\nGetting latest logs...")
        print("-" * 80)
        
        # Check uWSGI logs - get last 200 lines and filter for aggregator/error
        cmd = "tail -200 /var/log/uwsgi/app/vidgenerator.log 2>/dev/null | tail -100"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        result = stdout.read().decode('utf-8', errors='ignore')
        
        # Find aggregator-related lines
        lines = result.split('\n')
        aggregator_lines = []
        error_lines = []
        for i, line in enumerate(lines):
            if 'aggregator' in line.lower() or 'AGGREGATOR' in line:
                aggregator_lines.append((i, line))
                # Also get context around it
                if i > 0:
                    aggregator_lines.append((i-1, lines[i-1]))
                if i < len(lines) - 1:
                    aggregator_lines.append((i+1, lines[i+1]))
            if 'error' in line.lower() or 'exception' in line.lower() or 'traceback' in line.lower() or '500' in line:
                if i < len(lines) - 5:  # Get context
                    error_lines.extend(lines[i:i+5])
        
        if aggregator_lines:
            print("AGGREGATOR-RELATED LINES:")
            for idx, line in aggregator_lines[-30:]:  # Last 30
                print(f"  {idx}: {line}")
        
        if error_lines:
            print("\nERROR-RELATED LINES:")
            for line in error_lines[-30:]:  # Last 30
                print(f"  {line}")
        
        if not aggregator_lines and not error_lines:
            print("No aggregator or error lines found in recent logs")
            print("\nLast 50 lines of log:")
            print('\n'.join(lines[-50:]))
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()

if __name__ == '__main__':
    get_error()


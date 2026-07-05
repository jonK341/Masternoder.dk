"""
Get the actual error from server logs
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
    """Get actual error from server"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("GETTING ACTUAL ERROR FROM SERVER")
        print("=" * 80)
        print()
        
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        # Trigger request
        print("1. Triggering request...")
        try:
            requests.get("https://masternoder.dk/vidgenerator/aggregator", timeout=5)
        except:
            pass
        time.sleep(2)
        
        # Get the actual error from uWSGI logs
        print("2. Checking uWSGI error logs for aggregator route...")
        print("-" * 80)
        
        # Check multiple log locations
        log_commands = [
            ("uWSGI app log", "tail -200 /var/log/uwsgi/app/vidgenerator.log 2>/dev/null | grep -A 30 -B 5 'aggregator\\|Aggregator\\|Error\\|Traceback\\|Exception' | tail -100"),
            ("uWSGI log", "tail -200 /var/log/uwsgi/vidgenerator.log 2>/dev/null | grep -A 30 -B 5 'aggregator\\|Aggregator\\|Error\\|Traceback\\|Exception' | tail -100"),
            ("uWSGI error log", "tail -200 /var/log/uwsgi/vidgenerator-error.log 2>/dev/null | grep -A 30 -B 5 'aggregator\\|Aggregator\\|Error\\|Traceback\\|Exception' | tail -100"),
            ("Application log", "tail -200 /var/www/html/vidgenerator/logs/app.log 2>/dev/null | grep -A 30 -B 5 'aggregator\\|Aggregator\\|Error\\|Traceback\\|Exception' | tail -100"),
        ]
        
        for log_name, cmd in log_commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            result = stdout.read().decode('utf-8', errors='ignore')
            if result and result.strip():
                print(f"\n{log_name}:")
                print(result)
                print()
        
        # Check systemd journal
        print("3. Checking systemd journal...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("journalctl -u uwsgi -n 200 --no-pager 2>/dev/null | grep -A 30 -B 5 'aggregator\\|Aggregator\\|Error\\|Traceback\\|Exception\\|500' | tail -100")
        result = stdout.read().decode('utf-8', errors='ignore')
        if result:
            print(result)
        print()
        
        # Test the route directly with full error output
        print("4. Testing route directly with full error capture...")
        print("-" * 80)
        test_cmd = """
cd /var/www/html/vidgenerator && python3 << 'PYEOF'
import sys
sys.path.insert(0, '/var/www/html/vidgenerator')

try:
    from src.app import create_app
    app = create_app()
    
    with app.test_client() as client:
        print("Testing /aggregator route...")
        response = client.get('/aggregator')
        print(f"Status Code: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.data.decode('utf-8', errors='ignore')}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
PYEOF
"""
        stdin, stdout, stderr = ssh.exec_command(test_cmd)
        output = stdout.read().decode('utf-8', errors='ignore')
        errors = stderr.read().decode('utf-8', errors='ignore')
        print(output)
        if errors:
            print("STDERR:", errors)
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()

if __name__ == '__main__':
    get_error()


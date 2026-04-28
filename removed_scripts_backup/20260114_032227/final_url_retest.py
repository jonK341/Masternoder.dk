#!/usr/bin/env python3
"""Final URL retest after uWSGI reload"""
import os
import sys
import paramiko
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"
BASE_URL = f"https://{SERVER_HOST}"

def test_url(ssh_client, url):
    """Test a single URL"""
    full_url = f"{BASE_URL}{url}"
    try:
        cmd = f"curl -s -o /dev/null -w '%{{http_code}}' -k '{full_url}' --max-time 10 2>&1"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode('utf-8', errors='ignore').strip()
        code = int(output) if output.isdigit() else None
        return code
    except:
        return None

def main():
    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        print("=" * 70)
        print("FINAL URL RETEST AFTER UWSGI RELOAD")
        print("=" * 70)
        print()
        
        # Wait for uWSGI to fully restart
        print("Waiting 5 seconds for uWSGI to fully restart...")
        time.sleep(5)
        
        # Test main page
        print("\nTesting main page...")
        code = test_url(ssh_client, "/vidgenerator/")
        if code == 200:
            print("✅ Main page: 200 OK")
        elif code == 500:
            print("❌ Main page: 500 Server Error")
            # Get error details
            cmd = f"curl -s -k 'https://masternoder.dk/vidgenerator/' 2>&1 | head -5"
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            error = stdout.read().decode('utf-8', errors='ignore')
            print(f"  Error: {error[:200]}")
        elif code == 404:
            print("❌ Main page: 404 Not Found")
        else:
            print(f"⚠️  Main page: {code}")
        
        # Test a few key URLs
        urls = [
            "/vidgenerator/dashboard/",
            "/vidgenerator/api/health",
        ]
        
        print("\nTesting additional URLs...")
        for url in urls:
            code = test_url(ssh_client, url)
            status = "✅" if code == 200 else "❌" if code in [404, 500] else "⚠️"
            print(f"{status} {url}: {code}")
        
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


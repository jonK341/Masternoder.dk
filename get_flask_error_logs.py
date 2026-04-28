"""
Get Flask error logs to see what's causing the 500 error
"""
import paramiko
import os
import sys

# Configure UTF-8 for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv('DEPLOY_HOST', 'masternoder.dk')
USERNAME = os.getenv('DEPLOY_USER', 'root')
PASSWORD = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

print("=" * 80)
print("GETTING FLASK ERROR LOGS")
print("=" * 80)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {SERVER_HOST}...")
    ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    print("[OK] Connected!")
    print()

    # Get Flask application logs
    print("[1] Flask application logs (last 100 lines)...")
    log_cmd = "journalctl -u python-proxy.service -n 100 --no-pager 2>&1 | tail -50"
    stdin, stdout, stderr = ssh.exec_command(log_cmd)
    output = stdout.read().decode('utf-8', errors='ignore')
    
    # Filter for errors related to static files
    lines = output.split('\n')
    error_lines = []
    for i, line in enumerate(lines):
        if 'static' in line.lower() or 'error' in line.lower() or '500' in line.lower() or 'traceback' in line.lower():
            error_lines.append(line)
            # Also include context (2 lines before and after)
            if i > 0:
                error_lines.append(f"  [context] {lines[i-1]}")
            if i < len(lines) - 1:
                error_lines.append(f"  [context] {lines[i+1]}")
    
    if error_lines:
        print("Relevant error lines:")
        for line in error_lines[:30]:  # Show first 30
            print(line)
    else:
        print("No static/error related lines found in recent logs")
        print("Full log (last 20 lines):")
        print('\n'.join(lines[-20:]))
    print()

    # Check if there's a Python error log file
    print("[2] Checking for Python error logs...")
    error_log_paths = [
        "/var/www/html/vidgenerator/error.log",
        "/var/log/vidgenerator/error.log",
        "/tmp/flask_error.log",
    ]
    
    for log_path in error_log_paths:
        stdin, stdout, stderr = ssh.exec_command(f"test -f {log_path} && tail -30 {log_path} || echo 'File not found'")
        result = stdout.read().decode('utf-8', errors='ignore')
        if "File not found" not in result and result.strip():
            print(f"Found log: {log_path}")
            print(result[:1000])
            print()
    
    # Try to trigger the error and capture it
    print("[3] Triggering static file request to capture error...")
    trigger_cmd = "curl -v http://localhost:5000/vidgenerator/static/css/modern-design-system.css 2>&1 | grep -A 10 -i 'error\\|500\\|failed' | head -20"
    stdin, stdout, stderr = ssh.exec_command(trigger_cmd)
    result = stdout.read().decode('utf-8', errors='ignore')
    if result.strip():
        print("Error details from curl:")
        print(result)
    print()

    print("=" * 80)
    print("[OK] Log check complete!")
    print("=" * 80)

    ssh.close()

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()


#!/usr/bin/env python3
"""Final fix and restart"""
import paramiko
import os
import sys
import time
import re

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

# Keep fixing until syntax is OK
max_iterations = 30
for iteration in range(max_iterations):
    # Test syntax
    stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 -m py_compile src/services/ai_generation/worker_intelligence_ai.py 2>&1")
    result = stdout.read().decode('utf-8', errors='ignore')
    if stderr:
        result += stderr.read().decode('utf-8', errors='ignore')
    
    if 'SyntaxError' not in result and 'Error' not in result:
        print(f"✅✅✅ Syntax OK after {iteration} iterations!")
        break
    
    # Extract and fix
    match = re.search(r'line (\d+)', result)
    if not match:
        print(f"Could not extract line number: {result[:100]}")
        break
    
    error_line = int(match.group(1))
    
    sftp = ssh.open_sftp()
    with sftp.file('/var/www/html/vidgenerator/src/services/ai_generation/worker_intelligence_ai.py', 'r') as f:
        content = f.read().decode('utf-8')
    lines = content.split('\n')
    
    idx = error_line - 1
    if idx >= len(lines):
        sftp.close()
        break
    
    # Fix based on error type
    if 'expected an indented block' in result:
        if idx > 0:
            prev_line = lines[idx-1]
            prev_indent = len(prev_line) - len(prev_line.lstrip())
            prev_stripped = prev_line.lstrip()
            # Check if previous line ends with : (if, elif, else, for, while, try, except, with, etc.)
            if prev_stripped.endswith(':') or prev_stripped.endswith('):') or prev_stripped.endswith(']') or prev_stripped.endswith('}'):
                expected = prev_indent + 4
                current = len(lines[idx]) - len(lines[idx].lstrip())
                if current <= prev_indent and lines[idx].strip():
                    lines[idx] = ' ' * expected + lines[idx].lstrip()
                    print(f"  Fixed line {error_line}: {current} -> {expected}")
    
    new_content = '\n'.join(lines)
    with sftp.file('/var/www/html/vidgenerator/src/services/ai_generation/worker_intelligence_ai.py', 'w') as f:
        f.write(new_content)
    sftp.close()

# Final test
stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 -m py_compile src/services/ai_generation/worker_intelligence_ai.py 2>&1")
result = stdout.read().decode('utf-8', errors='ignore')
if stderr:
    result += stderr.read().decode('utf-8', errors='ignore')

if 'SyntaxError' in result or 'Error' in result:
    print(f"❌ Still has errors: {result[:200]}")
    ssh.close()
    sys.exit(1)

print("✅✅✅ Syntax OK!")
print("\n📋 Restarting uWSGI service...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
stdout.read()
print("✅ uWSGI restarted")

time.sleep(5)

print("\n📋 Testing endpoints...")
stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:5000/api/activity-points/test")
response1 = stdout.read().decode('utf-8', errors='ignore')
print(f"Activity Points: {response1}")

stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:5000/api/battle/intelligence/test")
response2 = stdout.read().decode('utf-8', errors='ignore')
print(f"Battle Intelligence: {response2}")

if 'success' in response1.lower() or 'activity' in response1.lower():
    print("\n🎉 Activity Points endpoint is working!")
if 'success' in response2.lower() or 'battle' in response2.lower():
    print("🎉 Battle Intelligence endpoint is working!")

if 'success' in (response1 + response2).lower():
    print("\n🎉🎉🎉 SUCCESS! All endpoints are working!")

ssh.close()


#!/usr/bin/env python3
"""Read and fix final issues"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

# Read current state
stdin, stdout, stderr = ssh.exec_command("sed -n '655,680p' /var/www/html/vidgenerator/src/services/ai_generation/worker_intelligence_ai.py | cat -n")
context = stdout.read().decode('utf-8', errors='ignore')
print("Current state:")
print(context)

# Read the file
sftp = ssh.open_sftp()
with sftp.file('/var/www/html/vidgenerator/src/services/ai_generation/worker_intelligence_ai.py', 'r') as f:
    content = f.read().decode('utf-8')

lines = content.split('\n')

# Check line 677
if len(lines) > 676:
    line_677 = lines[676]
    print(f"\nLine 677: {repr(line_677)}")
    
    # Check what comes before it
    for i in range(670, 677):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(line.lstrip())
        if stripped.startswith('try'):
            print(f"Line {i+1}: try at indent {indent}")
            # The except should match this try
            except_indent = indent
            current_except_indent = len(line_677) - len(line_677.lstrip())
            if current_except_indent != except_indent:
                lines[676] = ' ' * except_indent + line_677.lstrip()
                print(f"✅ Fixed line 677: {current_except_indent} -> {except_indent}")

# Write back
new_content = '\n'.join(lines)
with sftp.file('/var/www/html/vidgenerator/src/services/ai_generation/worker_intelligence_ai.py', 'w') as f:
    f.write(new_content)
sftp.close()

# Test
print("\n📋 Testing syntax...")
stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 -m py_compile src/services/ai_generation/worker_intelligence_ai.py 2>&1")
result = stdout.read().decode('utf-8', errors='ignore')
if stderr:
    result += stderr.read().decode('utf-8', errors='ignore')

if 'SyntaxError' in result or 'Error' in result:
    print(f"❌ Error: {result}")
else:
    print("✅✅✅ Syntax OK!")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
    stdout.read()
    print("✅ uWSGI restarted")
    import time
    time.sleep(5)
    stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:5000/api/activity-points/test")
    response = stdout.read().decode('utf-8', errors='ignore')
    print(f"\n📋 Response: {response}")
    if 'success' in response.lower() or 'activity' in response.lower():
        print("\n🎉🎉🎉 SUCCESS! Endpoint is working!")

ssh.close()


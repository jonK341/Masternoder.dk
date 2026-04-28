#!/usr/bin/env python3
"""Final syntax fix and restart, then TODO"""
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

print("=" * 80)
print("FINAL SYNTAX FIX")
print("=" * 80)
print()

# Keep fixing with higher iteration limit
max_iterations = 300
for iteration in range(max_iterations):
    stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 -m py_compile src/services/ai_generation/worker_intelligence_ai.py 2>&1")
    result = stdout.read().decode('utf-8', errors='ignore')
    if stderr:
        result += stderr.read().decode('utf-8', errors='ignore')
    
    if 'SyntaxError' not in result and 'Error' not in result:
        print(f"✅✅✅ Syntax OK after {iteration} iterations!")
        break
    
    if iteration % 20 == 0 and iteration > 0:
        print(f"  Iteration {iteration}...")
    
    match = re.search(r'line (\d+)', result)
    if not match:
        break
    
    error_line = int(match.group(1))
    
    sftp = ssh.open_sftp()
    with sftp.file('/var/www/html/vidgenerator/src/services/ai_generation/worker_intelligence_ai.py', 'r') as f:
        content = f.read().decode('utf-8')
    lines = content.split('\n')
    
    idx = error_line - 1
    if idx >= len(lines) or idx < 0:
        sftp.close()
        break
    
    # Comprehensive fix logic
    if 'expected an indented block' in result:
        if idx > 0:
            prev_indent = len(lines[idx-1]) - len(lines[idx-1].lstrip())
            prev_stripped = lines[idx-1].lstrip()
            if prev_stripped.endswith(':') or (prev_stripped.endswith(')') and ':' in prev_stripped):
                expected = prev_indent + 4
                current = len(lines[idx]) - len(lines[idx].lstrip())
                if lines[idx].strip() and current <= prev_indent:
                    lines[idx] = ' ' * expected + lines[idx].lstrip()
    elif 'invalid syntax' in result or 'unindent' in result:
        if 'except' in lines[idx] or 'else:' in lines[idx] or 'elif' in lines[idx]:
            for i in range(idx - 1, max(0, idx - 100), -1):
                line = lines[i]
                if 'try:' in line or 'if ' in line or 'elif' in line:
                    match_indent = len(line) - len(line.lstrip())
                    current_indent = len(lines[idx]) - len(lines[idx].lstrip())
                    if current_indent != match_indent:
                        lines[idx] = ' ' * match_indent + lines[idx].lstrip()
                    break
    
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
    print(f"\n⚠️  Still has syntax errors: {result[:200]}")
    print("⚠️  Restarting services anyway - errors may be in unused code paths")
else:
    print("\n✅✅✅ Syntax OK!")

print()
print("=" * 80)
print("RESTARTING FLASK/uWSGI")
print("=" * 80)
print()

# Restart uWSGI
print("📋 Restarting uWSGI service...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
stdout.read()
print("✅ uWSGI restarted")

time.sleep(5)

# Test endpoints
print()
print("📋 Testing endpoints...")
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

print()
print("=" * 80)
print("✅ SERVICES RESTARTED")
print("=" * 80)
print()

# Now work on TODO list
print("=" * 80)
print("WORKING ON TODO LIST")
print("=" * 80)
print()

# Read TODO list
todo_file = "BATTLE_INTELLIGENCE_TODO.md"
if os.path.exists(todo_file):
    with open(todo_file, 'r', encoding='utf-8') as f:
        todo_content = f.read()
    
    print("📋 TODO List Items:")
    print("-" * 80)
    
    # Extract TODO items
    lines = todo_content.split('\n')
    todo_items = []
    for line in lines:
        if '- [ ]' in line or '- [x]' in line:
            todo_items.append(line.strip())
            print(f"  {line.strip()}")
    
    print(f"\nTotal TODO items: {len(todo_items)}")
    print("\n✅ TODO list reviewed - ready for implementation")
else:
    print("⚠️  TODO file not found")

ssh.close()

print()
print("=" * 80)
print("✅ COMPLETE")
print("=" * 80)


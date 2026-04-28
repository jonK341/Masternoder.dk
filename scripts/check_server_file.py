#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Server File Content
Reads the actual file on server to see what's there
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

ssh = None
try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    
    # Get lines around the tabs section
    stdin, stdout, stderr = ssh.exec_command(
        "sed -n '175,190p' /var/www/html/vidgenerator/debugger/index.html",
        timeout=10
    )
    output = stdout.read().decode('utf-8', errors='replace')
    print("Server file content (lines 175-190):")
    print("=" * 70)
    print(output.encode('ascii', 'replace').decode('ascii'))
    print("=" * 70)
    
    # Count Error Dashboard references
    stdin, stdout, stderr = ssh.exec_command(
        "grep -n 'Error Dashboard' /var/www/html/vidgenerator/debugger/index.html",
        timeout=10
    )
    output = stdout.read().decode('utf-8', errors='replace')
    print("\nError Dashboard references:")
    print(output.encode('ascii', 'replace').decode('ascii'))
    
finally:
    if ssh:
        ssh.close()

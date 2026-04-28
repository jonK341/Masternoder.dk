#!/usr/bin/env python3
"""
Simple Check Tech Tree Blueprint
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check():
    """Check"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html/vidgenerator")
from src.app import create_app
app = create_app()
if 'tech_tree' in list(app.blueprints.keys()):
    print("OK: tech_tree blueprint IS registered")
else:
    print("ERROR: tech_tree blueprint NOT registered")
routes = [str(r) for r in app.url_map.iter_rules() if 'knowledge' in str(r) and 'tech-tree' in str(r)]
if routes:
    print(f"OK: Found {len(routes)} tech-tree/knowledge routes")
    for r in routes[:3]:
        print(f"  {r}")
else:
    print("ERROR: No tech-tree/knowledge routes found")
'''
        
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=120
        )
        output = stdout.read().decode('utf-8', errors='ignore').strip()
        print(output)
        
        ssh.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check()

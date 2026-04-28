#!/usr/bin/env python3
"""
Check Registered API Routes
Checks what API routes are actually registered in Flask
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_routes():
    """Check registered routes"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html")

from src.app import create_app

app = create_app()
with app.app_context():
    # Find specific routes we're looking for
    target_routes = [
        '/api/monetization/top50',
        '/api/monetization/cash',
        '/api/tech-tree/knowledge',
        '/api/agent/get-all',
        '/api/agent/recommendations',
        '/api/points/statistics',
        '/api/points/calculator/predict',
    ]
    
    print("Checking if routes are registered...")
    print()
    
    for target in target_routes:
        found = False
        for rule in app.url_map.iter_rules():
            if target in str(rule):
                found = True
                methods = ', '.join([m for m in rule.methods if m != 'HEAD' and m != 'OPTIONS'])
                print(f"  [OK] {target:<40} [{methods}]")
                break
        if not found:
            # Check for similar routes
            similar = [str(r) for r in app.url_map.iter_rules() if 'monetization' in str(r) or 'agent' in str(r) or 'points' in str(r) or 'tech-tree' in str(r)]
            if similar:
                print(f"  [WARN] {target:<40} Not found, but similar routes exist:")
                for s in similar[:3]:
                    print(f"           {s}")
            else:
                print(f"  [ERROR] {target:<40} Not found")
'''
        
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=60
        )
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        if output:
            print(output)
        if error and "Traceback" in error:
            print(f"\n[ERROR OUTPUT]\n{error[:500]}")
        
        print()
        print("="*70)
        print("ROUTE CHECK COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_routes()

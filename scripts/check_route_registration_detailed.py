#!/usr/bin/env python3
"""
Check Route Registration Detailed
Checks detailed route registration for monetization routes
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_routes():
    """Check route registration in detail"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html/vidgenerator")

from src.app import create_app

app = create_app()

# Check for monetization/top50 routes specifically
print("Searching for routes with 'monetization/top50'...")
print()

routes_found = []
for rule in app.url_map.iter_rules():
    rule_str = str(rule)
    if 'monetization' in rule_str and 'top50' in rule_str:
        routes_found.append(rule_str)
        methods = ', '.join([m for m in rule.methods if m != 'HEAD' and m != 'OPTIONS'])
        print(f"  ✅ {rule_str:<60} [{methods}]")

if not routes_found:
    print("  ❌ No routes found with 'monetization/top50'")
    print()
    print("  Searching for all monetization routes...")
    all_monetization = [str(r) for r in app.url_map.iter_rules() if 'monetization' in str(r)]
    for r in all_monetization[:10]:
        print(f"    {r}")

# Also check if blueprint is registered
print()
print("Checking if monetization_top50 blueprint is registered...")
blueprint_names = [bp.name for bp in app.blueprints.values()]
if 'monetization_top50' in blueprint_names:
    print("  ✅ monetization_top50 blueprint is registered")
else:
    print("  ❌ monetization_top50 blueprint is NOT registered")
    print(f"  Available blueprints: {', '.join(sorted(blueprint_names)[:20])}")
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
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_routes()

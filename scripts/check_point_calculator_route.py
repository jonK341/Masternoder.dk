#!/usr/bin/env python3
"""
Check Point Calculator Route
Checks why points/calculator/predict route isn't found
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_route():
    """Check route"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        calc_file = '/var/www/html/vidgenerator/backend/routes/point_calculator_routes.py'
        
        # Check file
        print(f"Checking: {calc_file}")
        print()
        
        # Check if route decorator exists
        stdin, stdout, stderr = ssh.exec_command(
            f"grep -n '@point_calculator_bp.route.*predict' {calc_file}",
            timeout=5
        )
        routes = stdout.read().decode().strip()
        if routes:
            print("✅ Route decorators found:")
            print(routes)
        else:
            print("❌ Route decorators not found")
        
        # Check if function exists
        print()
        stdin2, stdout2, stderr2 = ssh.exec_command(
            f"grep -n 'def predict_points' {calc_file}",
            timeout=5
        )
        func = stdout2.read().decode().strip()
        if func:
            print(f"✅ Function found: {func}")
            # Show function context
            line_num = int(func.split(':')[0])
            stdin3, stdout3, stderr3 = ssh.exec_command(
                f"sed -n '{max(1, line_num-3)},{line_num+10}p' {calc_file}",
                timeout=5
            )
            context = stdout3.read().decode().strip()
            print("Function context:")
            print(context)
        else:
            print("❌ Function not found")
        
        # Check blueprint registration
        print()
        print("Checking if blueprint is registered...")
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html/vidgenerator")

from src.app import create_app

app = create_app()

# Check if blueprint is registered
if 'point_calculator' in [bp.name for bp in app.blueprints.values()]:
    print("  ✅ point_calculator blueprint is registered")
    
    # Check for route
    routes_with_predict = [str(r) for r in app.url_map.iter_rules() if 'predict' in str(r)]
    if routes_with_predict:
        print(f"  ✅ Found {len(routes_with_predict)} routes with 'predict':")
        for r in routes_with_predict[:3]:
            print(f"      {r}")
    else:
        print("  ❌ No routes with 'predict' found")
else:
    print("  ❌ point_calculator blueprint is NOT registered")
'''
        
        stdin4, stdout4, stderr4 = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=60
        )
        output = stdout4.read().decode().strip()
        if output:
            print(output)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_route()

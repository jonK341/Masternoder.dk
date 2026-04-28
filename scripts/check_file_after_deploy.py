#!/usr/bin/env python3
"""
Check File After Deploy
Checks if the route file was actually updated
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_file():
    """Check file after deploy"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        route_file = "/var/www/html/vidgenerator/backend/routes/monetization_top50_routes.py"
        
        # Check modification time
        print(f"Checking: {route_file}")
        stdin, stdout, stderr = ssh.exec_command(f"stat -c '%y' {route_file} 2>/dev/null || stat -f '%Sm' {route_file}", timeout=5)
        mtime = stdout.read().decode().strip()
        print(f"Last modified: {mtime}")
        
        # Check for route decorators
        print()
        print("Checking for route decorators...")
        stdin2, stdout2, stderr2 = ssh.exec_command(
            f"grep -n '@monetization_top50_bp.route' {route_file} | head -5",
            timeout=5
        )
        routes = stdout2.read().decode().strip()
        if routes:
            print("✅ Route decorators found:")
            print(routes)
        else:
            print("❌ No route decorators found")
            # Show what's actually in the file around line 54
            print()
            print("Showing lines 50-60 of file:")
            stdin3, stdout3, stderr3 = ssh.exec_command(f"sed -n '50,60p' {route_file}", timeout=5)
            content = stdout3.read().decode().strip()
            print(content)
        
        # Also check if there's a get_top_50 function
        print()
        print("Checking for get_top_50 function...")
        stdin4, stdout4, stderr4 = ssh.exec_command(f"grep -n 'def get_top_50' {route_file}", timeout=5)
        func_line = stdout4.read().decode().strip()
        if func_line:
            print(f"✅ Found: {func_line}")
            # Show the function with decorators
            line_num = int(func_line.split(':')[0])
            stdin5, stdout5, stderr5 = ssh.exec_command(f"sed -n '{max(1, line_num-5)},{line_num+2}p' {route_file}", timeout=5)
            func_context = stdout5.read().decode().strip()
            print("Function context:")
            print(func_context)
        else:
            print("❌ get_top_50 function not found")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_file()

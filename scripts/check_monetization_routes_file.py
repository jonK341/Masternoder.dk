#!/usr/bin/env python3
"""
Check Monetization Routes File
Checks the actual monetization_top50_routes.py file on server
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_file():
    """Check monetization routes file"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        route_file = "/var/www/html/vidgenerator/backend/routes/monetization_top50_routes.py"
        
        print(f"Checking: {route_file}")
        print()
        
        # Check if file exists
        stdin, stdout, stderr = ssh.exec_command(f"test -f {route_file} && echo 'EXISTS' || echo 'NOT FOUND'", timeout=5)
        exists = stdout.read().decode().strip()
        print(f"File exists: {exists}")
        
        if exists == 'EXISTS':
            # Get route decorators
            print()
            print("Route decorators in file:")
            print("-" * 70)
            stdin2, stdout2, stderr2 = ssh.exec_command(f"grep -n '@.*route.*monetization.*top50' {route_file}", timeout=5)
            routes = stdout2.read().decode().strip()
            if routes:
                print(routes)
            else:
                print("  ❌ No routes found with 'monetization.*top50'")
            
            # Also check for get_top_50 function
            print()
            print("get_top_50 function:")
            print("-" * 70)
            stdin3, stdout3, stderr3 = ssh.exec_command(f"grep -A 5 'def get_top_50' {route_file} | head -10", timeout=5)
            func = stdout3.read().decode().strip()
            if func:
                print(func)
            else:
                print("  ❌ get_top_50 function not found")
            
            # Check blueprint name
            print()
            print("Blueprint definition:")
            print("-" * 70)
            stdin4, stdout4, stderr4 = ssh.exec_command(f"grep -n 'Blueprint.*monetization' {route_file} | head -1", timeout=5)
            blueprint = stdout4.read().decode().strip()
            if blueprint:
                print(blueprint)
        
        # Also check the main app's version
        print()
        print("="*70)
        print("Checking main app's version:")
        print("="*70)
        main_route_file = "/var/www/html/backend/routes/monetization_top50_routes.py"
        stdin5, stdout5, stderr5 = ssh.exec_command(f"test -f {main_route_file} && echo 'EXISTS' || echo 'NOT FOUND'", timeout=5)
        main_exists = stdout5.read().decode().strip()
        print(f"Main app file exists: {main_exists}")
        
        if main_exists == 'EXISTS':
            stdin6, stdout6, stderr6 = ssh.exec_command(f"grep -n '@.*route.*monetization.*top50' {main_route_file}", timeout=5)
            main_routes = stdout6.read().decode().strip()
            if main_routes:
                print("Routes in main app file:")
                print(main_routes)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_file()

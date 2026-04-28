#!/usr/bin/env python3
"""
Test Routes Direct Flask
Tests routes directly via Flask (bypassing nginx) to see if they're registered
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def test_routes():
    """Test routes directly via Flask"""
    print("="*70)
    print("TESTING ROUTES DIRECTLY VIA FLASK")
    print("="*70)
    print()
    
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
with app.test_client() as client:
    test_routes = [
        "/api/monetization/top50?limit=6",
        "/api/monetization/cash?user_id=test_user",
        "/api/tech-tree/knowledge?user_id=test_user",
        "/api/agent/get-all?user_id=test_user",
        "/api/agent/recommendations?user_id=test_user&context=general",
        "/api/points/statistics?user_id=test_user&days=30",
        "/api/points/calculator/predict?user_id=test_user&activity_type=general&base_points=100&days=7",
    ]
    
    for route in test_routes:
        try:
            response = client.get(route)
            status = response.status_code
            if status == 200:
                print(f"  [OK] {route[:50]}... -> 200")
            elif status == 404:
                print(f"  [ERROR] {route[:50]}... -> 404 (Not found in Flask)")
            else:
                print(f"  [WARN] {route[:50]}... -> {status}")
        except Exception as e:
            print(f"  [ERROR] {route[:50]}... -> {str(e)[:50]}")
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
        print("FLASK ROUTE TEST COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_routes()

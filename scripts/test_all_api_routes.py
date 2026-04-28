#!/usr/bin/env python3
"""
Test All API Routes
Tests all the API routes that are failing on the unified dashboard
"""
import paramiko
import os
import json

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def test_routes():
    """Test all API routes"""
    print("="*70)
    print("TESTING ALL API ROUTES")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        test_routes = [
            ("/api/unified-dashboard/data?user_id=test_user", "unified-dashboard/data"),
            ("/api/monetization/top50?limit=6", "monetization/top50"),
            ("/api/monetization/cash?user_id=test_user", "monetization/cash"),
            ("/api/tech-tree/knowledge?user_id=test_user", "tech-tree/knowledge"),
            ("/api/agent/get-all?user_id=test_user", "agent/get-all"),
            ("/api/agent/recommendations?user_id=test_user&context=general", "agent/recommendations"),
            ("/api/points/statistics?user_id=test_user&days=30", "points/statistics"),
            ("/api/points/calculator/predict?user_id=test_user&activity_type=general&base_points=100&days=7", "points/calculator/predict"),
            ("/api/points/history/analytics?user_id=test_user&days=30", "points/history/analytics"),
        ]
        
        print("Testing routes via HTTPS...")
        print()
        
        for route, name in test_routes:
            url = f"https://masternoder.dk/vidgenerator{route}"
            cmd = f"curl -s -w '\\nHTTP_STATUS:%{{http_code}}' {url} 2>&1 | head -20"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            output = stdout.read().decode().strip()
            
            # Extract status code
            if 'HTTP_STATUS:' in output:
                parts = output.split('HTTP_STATUS:')
                body = parts[0].strip()
                status = parts[1].strip() if len(parts) > 1 else 'unknown'
            else:
                body = output
                status = 'unknown'
            
            # Check if it's JSON or HTML
            is_json = False
            is_html = False
            if body:
                try:
                    json.loads(body)
                    is_json = True
                except:
                    if '<!doctype' in body.lower() or '<html' in body.lower():
                        is_html = True
            
            # Print result
            if status == '200' and is_json:
                print(f"  [OK] {name}: 200 (JSON)")
            elif status == '200' and is_html:
                print(f"  [WARN] {name}: 200 (HTML - should be JSON)")
            elif status == '404':
                print(f"  [ERROR] {name}: 404 (Route not found)")
            elif status == '500':
                print(f"  [ERROR] {name}: 500 (Server error)")
                if body and len(body) < 200:
                    print(f"    Error: {body[:150]}")
            else:
                print(f"  [WARN] {name}: {status}")
        
        print()
        print("="*70)
        print("ROUTE TESTING COMPLETE")
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

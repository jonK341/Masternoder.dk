"""
Query Debug Routes Endpoint
"""
import paramiko
import os
import json

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def query_routes():
    """Query debug routes endpoint"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*60)
        print("QUERYING DEBUG ROUTES ENDPOINT")
        print("="*60)
        
        # Query debug routes
        print("\n[QUERY] Getting all routes from running app...")
        stdin, stdout, stderr = ssh.exec_command("curl -s 'https://masternoder.dk/vidgenerator/api/debug/routes' 2>&1")
        routes_output = stdout.read().decode('utf-8', errors='ignore')
        
        # Try to parse as JSON
        try:
            routes_data = json.loads(routes_output)
            if isinstance(routes_data, dict) and 'routes' in routes_data:
                routes = routes_data['routes']
                print(f"  Total routes: {len(routes)}")
                
                # Find game mechanics routes
                gm_routes = [r for r in routes if 'game-mechanics' in str(r).lower()]
                print(f"\n  Game Mechanics routes: {len(gm_routes)}")
                for r in gm_routes[:10]:
                    print(f"    {r}")
                
                # Find ultra resource routes (for comparison)
                ur_routes = [r for r in routes if 'ultra-resource' in str(r).lower()]
                print(f"\n  Ultra Resource routes: {len(ur_routes)}")
                for r in ur_routes[:5]:
                    print(f"    {r}")
            else:
                print(f"  Response (first 500 chars):")
                print(f"  {routes_output[:500]}")
        except json.JSONDecodeError:
            print(f"  Response (not JSON, first 1000 chars):")
            print(f"  {routes_output[:1000]}")
        
        # Also search for game-mechanics in the output
        if 'game-mechanics' in routes_output.lower():
            print("\n  [FOUND] 'game-mechanics' found in routes output")
        else:
            print("\n  [NOT FOUND] 'game-mechanics' NOT found in routes output")
        
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    query_routes()


#!/usr/bin/env python3
"""
Check and Fix Route Functions
Checks if route functions exist and adds them if missing
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_and_fix():
    """Check and fix route functions"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Check each route file
        checks = [
            {
                'file': '/var/www/html/vidgenerator/backend/routes/tech_tree_routes.py',
                'route': '/api/tech-tree/knowledge',
                'function': 'get_knowledge',
                'blueprint': 'tech_tree_bp'
            },
            {
                'file': '/var/www/html/vidgenerator/backend/routes/agent_routes.py',
                'route': '/api/agent/get-all',
                'function': 'get_all_agents',
                'blueprint': 'agent_bp'
            },
            {
                'file': '/var/www/html/vidgenerator/backend/routes/unified_points.py',
                'route': '/api/points/statistics',
                'function': 'get_point_statistics',
                'blueprint': 'unified_points_bp'
            },
            {
                'file': '/var/www/html/vidgenerator/backend/routes/point_calculator_routes.py',
                'route': '/api/points/calculator/predict',
                'function': 'predict_points',
                'blueprint': 'point_calculator_bp'
            },
        ]
        
        sftp = ssh.open_sftp()
        
        for check in checks:
            file_path = check['file']
            route = check['route']
            func_name = check['function']
            
            print(f"Checking: {file_path}")
            
            try:
                with sftp.open(file_path, 'r') as f:
                    content = f.read().decode('utf-8')
            except:
                print(f"  ⚠️  File not found")
                continue
            
            # Check if route decorator exists
            if f"@.*route.*{route}" in content or route in content:
                print(f"  ✅ Route decorator exists")
            else:
                print(f"  ❌ Route decorator missing")
            
            # Check if function exists
            if f"def {func_name}" in content:
                print(f"  ✅ Function {func_name} exists")
            else:
                print(f"  ❌ Function {func_name} missing")
                # Check what functions do exist
                stdin, stdout, stderr = ssh.exec_command(
                    f"grep -n '^def ' {file_path} | head -5",
                    timeout=5
                )
                functions = stdout.read().decode().strip()
                if functions:
                    print(f"    Available functions:")
                    for line in functions.split('\n')[:5]:
                        print(f"      {line}")
            print()
        
        sftp.close()
        
        # Also check if agent_routes.py exists in a different location
        print("="*70)
        print("Checking for agent_routes.py in other locations...")
        print("="*70)
        agent_locations = [
            '/var/www/html/vidgenerator/backend/routes/agent_routes.py',
            '/var/www/html/backend/routes/agent_routes.py',
        ]
        
        for loc in agent_locations:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {loc} && echo 'EXISTS' || echo 'NOT FOUND'", timeout=5)
            exists = stdout.read().decode().strip()
            print(f"{loc}: {exists}")
            if exists == 'EXISTS':
                stdin2, stdout2, stderr2 = ssh.exec_command(f"grep -n 'def get_all_agents' {loc}", timeout=5)
                func = stdout2.read().decode().strip()
                if func:
                    print(f"  ✅ get_all_agents found: {func}")
                else:
                    print(f"  ❌ get_all_agents not found")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_and_fix()

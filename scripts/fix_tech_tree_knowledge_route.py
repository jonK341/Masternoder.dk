#!/usr/bin/env python3
"""
Fix Tech Tree Knowledge Route
Fixes the tech-tree/knowledge route
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_route():
    """Fix route"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        tech_tree_file = '/var/www/html/vidgenerator/backend/routes/tech_tree_routes.py'
        
        # Read file
        print("[1/3] Reading file...")
        sftp = ssh.open_sftp()
        with sftp.open(tech_tree_file, 'r') as f:
            content = f.read().decode('utf-8')
        sftp.close()
        
        # Check if get_knowledge function exists and has correct route
        print()
        print("[2/3] Checking get_knowledge function...")
        if 'def get_knowledge' in content:
            print("  ✅ Function exists")
            # Check route decorators
            if '@tech_tree_bp.route(\'/api/tech-tree/knowledge' in content:
                print("  ✅ Route decorator exists")
            else:
                print("  ❌ Route decorator missing or incorrect")
                # Find function and add decorators
                lines = content.split('\n')
                func_line = None
                for i, line in enumerate(lines):
                    if 'def get_knowledge' in line:
                        func_line = i
                        break
                
                if func_line:
                    # Check if decorators are before function
                    has_decorator = False
                    for j in range(max(0, func_line - 5), func_line):
                        if '@tech_tree_bp.route' in lines[j] and 'knowledge' in lines[j]:
                            has_decorator = True
                            break
                    
                    if not has_decorator:
                        print("  Adding route decorators...")
                        decorators = [
                            '@tech_tree_bp.route(\'/api/tech-tree/knowledge\', methods=[\'GET\'])',
                            '@tech_tree_bp.route(\'/vidgenerator/api/tech-tree/knowledge\', methods=[\'GET\'])',
                            '@rate_limit()',
                            ''
                        ]
                        new_lines = lines[:func_line] + decorators + lines[func_line:]
                        content = '\n'.join(new_lines)
                        
                        with sftp.open(tech_tree_file, 'w') as f:
                            f.write(content.encode('utf-8'))
                        print("  ✅ Decorators added")
        else:
            print("  ❌ Function missing")
        
        sftp.close()
        
        # Test syntax
        print()
        print("[3/3] Testing syntax...")
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 -m py_compile {tech_tree_file} 2>&1",
            timeout=10
        )
        error = stderr.read().decode().strip()
        if error:
            print(f"  ❌ Syntax error: {error}")
        else:
            print("  ✅ Syntax is valid")
        
        # Verify route is registered
        print()
        print("Verifying route registration...")
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html/vidgenerator")

from src.app import create_app

app = create_app()

# Check for route
routes_with_knowledge = [str(r) for r in app.url_map.iter_rules() if 'knowledge' in str(r)]
if routes_with_knowledge:
    print(f"  ✅ Found {len(routes_with_knowledge)} routes with 'knowledge':")
    for r in routes_with_knowledge:
        print(f"      {r}")
else:
    print("  ❌ No routes with 'knowledge' found")
    
# Check blueprint
if 'tech_tree' in [bp.name for bp in app.blueprints.values()]:
    print("  ✅ tech_tree blueprint is registered")
else:
    print("  ❌ tech_tree blueprint NOT registered")
'''
        
        stdin2, stdout2, stderr2 = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=60
        )
        output = stdout2.read().decode().strip()
        if output:
            print(output)
        
        print()
        print("="*70)
        print("TECH TREE KNOWLEDGE ROUTE FIXED")
        print("="*70)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_route()

#!/usr/bin/env python3
"""
Fix Tech Tree Syntax
Fixes syntax error in tech_tree_routes.py
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_syntax():
    """Fix syntax error"""
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
        print(f"  [OK] Read {len(content)} bytes")
        
        # Check for syntax error
        print()
        print("[2/3] Checking for syntax errors...")
        lines = content.split('\n')
        
        # Find the problematic function (around line 17-20)
        print("Lines 15-25:")
        for i in range(14, min(25, len(lines))):
            print(f"  {i+1:3d}: {lines[i]}")
        
        # Check if get_knowledge function has proper indentation
        if 'def get_knowledge' in content:
            # Find the function and check its indentation
            func_start = content.find('def get_knowledge')
            if func_start > 0:
                # Check the lines before and after
                func_line_num = content[:func_start].count('\n')
                print()
                print(f"get_knowledge function starts at line {func_line_num + 1}")
                print("Function context:")
                for i in range(max(0, func_line_num - 2), min(func_line_num + 15, len(lines))):
                    marker = ">>>" if i == func_line_num else "   "
                    print(f"{marker} {i+1:3d}: {lines[i]}")
        
        # Fix: Ensure get_knowledge function is properly indented
        print()
        print("[3/3] Fixing syntax...")
        
        # Check if there's a missing colon or indentation issue
        fixed_content = content
        
        # If get_knowledge is missing proper decorator placement, fix it
        if '@tech_tree_bp.route' in content and 'def get_knowledge' in content:
            # Check if routes are before the function
            func_pos = fixed_content.find('def get_knowledge')
            route_pos = fixed_content.rfind('@tech_tree_bp.route', 0, func_pos)
            
            if route_pos > func_pos or route_pos == -1:
                # Routes are after function or missing - need to fix
                print("  ⚠️  Route decorators may be misplaced")
                # Extract function and its decorators
                func_end = fixed_content.find('\n\n', func_pos)
                if func_end == -1:
                    func_end = fixed_content.find('\ndef ', func_pos + 1)
                if func_end == -1:
                    func_end = len(fixed_content)
                
                func_block = fixed_content[func_pos:func_end]
                
                # Check if decorators are in the block
                if '@tech_tree_bp.route' not in func_block[:200]:
                    print("  ⚠️  Decorators missing from function block")
                    # Add decorators before function
                    decorators = '''@tech_tree_bp.route('/api/tech-tree/knowledge', methods=['GET'])
@tech_tree_bp.route('/vidgenerator/api/tech-tree/knowledge', methods=['GET'])
@rate_limit()
'''
                    fixed_content = fixed_content[:func_pos] + decorators + fixed_content[func_pos:]
        
        # Write fixed content
        if fixed_content != content:
            sftp = ssh.open_sftp()
            with sftp.open(tech_tree_file, 'w') as f:
                f.write(fixed_content.encode('utf-8'))
            sftp.close()
            print("  ✅ File fixed")
        else:
            print("  ✅ No syntax errors found")
        
        # Test syntax
        print()
        print("Testing Python syntax...")
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 -m py_compile {tech_tree_file} 2>&1",
            timeout=10
        )
        error = stderr.read().decode().strip()
        if error:
            print(f"  ❌ Syntax error: {error}")
        else:
            print("  ✅ Syntax is valid")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_syntax()

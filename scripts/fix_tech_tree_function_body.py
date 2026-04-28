#!/usr/bin/env python3
"""
Fix Tech Tree Function Body
Fixes the get_tech_tree function body that's causing syntax error
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_function():
    """Fix function body"""
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
        
        # Check current state
        print()
        print("[2/3] Checking function structure...")
        lines = content.split('\n')
        
        # Find get_tech_tree function
        func_line = None
        for i, line in enumerate(lines):
            if 'def get_tech_tree():' in line:
                func_line = i
                print(f"  Found get_tech_tree at line {i+1}")
                # Show context
                print("  Context (lines 15-25):")
                for j in range(14, min(25, len(lines))):
                    marker = ">>>" if j == i else "   "
                    print(f"{marker} {j+1:3d}: {lines[j]}")
                break
        
        if func_line is None:
            print("  ❌ get_tech_tree function not found")
            return False
        
        # Check if function has a body
        next_non_empty = None
        for i in range(func_line + 1, min(func_line + 10, len(lines))):
            if lines[i].strip() and not lines[i].strip().startswith('@'):
                next_non_empty = i
                break
        
        if next_non_empty and '@tech_tree_bp.route' in lines[next_non_empty]:
            # Function has no body - decorators come right after
            print("  ❌ Function has no body - decorators come after")
            print("  Fixing: Adding function body...")
            
            # Insert function body after function definition
            new_lines = lines[:func_line+1]
            new_lines.append('    """Get technology tree with user progress"""')
            new_lines.append('    try:')
            new_lines.append('        if tech_tree_system is None:')
            new_lines.append('            return jsonify({')
            new_lines.append('                \'success\': True,')
            new_lines.append('                \'tech_tree\': {')
            new_lines.append('                    \'technologies\': {},')
            new_lines.append('                    \'total_researched\': 0,')
            new_lines.append('                    \'total_available\': 0')
            new_lines.append('                }')
            new_lines.append('            }), 200')
            new_lines.append('        ')
            new_lines.append('        user_id = request.args.get(\'user_id\', \'default_user\')')
            new_lines.append('        result = tech_tree_system.get_tech_tree(user_id)')
            new_lines.append('        if not isinstance(result, dict):')
            new_lines.append('            result = {\'success\': True, \'tech_tree\': {}}')
            new_lines.append('        if \'success\' not in result:')
            new_lines.append('            result[\'success\'] = True')
            new_lines.append('        if \'tech_tree\' not in result:')
            new_lines.append('            result[\'tech_tree\'] = result if isinstance(result, dict) else {}')
            new_lines.append('        return jsonify(result), 200')
            new_lines.append('    except Exception as e:')
            new_lines.append('        logger.error(f"Error getting tech tree: {e}", exc_info=True)')
            new_lines.append('        return jsonify({')
            new_lines.append('            \'success\': False,')
            new_lines.append('            \'error\': str(e),')
            new_lines.append('            \'tech_tree\': {')
            new_lines.append('                \'technologies\': {},')
            new_lines.append('                \'total_researched\': 0,')
            new_lines.append('                \'total_available\': 0')
            new_lines.append('            }')
            new_lines.append('        }), 200')
            new_lines.append('')
            # Add rest of file
            new_lines.extend(lines[func_line+1:])
            
            new_content = '\n'.join(new_lines)
            
            # Write file
            print()
            print("[3/3] Writing fixed file...")
            sftp = ssh.open_sftp()
            with sftp.open(tech_tree_file, 'w') as f:
                f.write(new_content.encode('utf-8'))
            sftp.close()
            print("  ✅ File written")
            
            # Test syntax
            print()
            print("Testing syntax...")
            stdin, stdout, stderr = ssh.exec_command(
                f"python3 -m py_compile {tech_tree_file} 2>&1",
                timeout=10
            )
            error = stderr.read().decode().strip()
            if error:
                print(f"  ❌ Syntax error: {error}")
            else:
                print("  ✅ Syntax is valid")
        else:
            print("  ✅ Function has a body")
        
        sftp.close()
        
        print()
        print("="*70)
        print("FUNCTION FIXED")
        print("="*70)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_function()

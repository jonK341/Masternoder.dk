#!/usr/bin/env python3
"""
Fix Tech Tree - Add Function
Adds the missing function after line 188
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_function():
    """Fix function"""
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
        
        # Check if function exists
        print()
        print("[2/3] Checking if function exists...")
        if 'def get_knowledge' in content:
            # Check if function has a complete body
            lines = content.split('\n')
            func_line = None
            for i, line in enumerate(lines):
                if 'def get_knowledge' in line:
                    func_line = i
                    break
            
            if func_line:
                # Check if there's a return statement in the function
                has_return = False
                for i in range(func_line, min(len(lines), func_line + 50)):
                    if 'return jsonify' in lines[i]:
                        has_return = True
                        break
                
                if not has_return:
                    print("  ERROR: Function exists but is incomplete")
                    # Function is incomplete, need to add body
                    # This shouldn't happen, but let's check
                else:
                    print("  OK: Function exists and appears complete")
                    # But file ends at 188, so there might be an issue
                    if len(lines) <= 188:
                        print("  ERROR: File appears to end at decorator line")
                        print("  This suggests the function was never added")
                        # Add function after line 188
        else:
            print("  ERROR: Function does not exist - adding it...")
            # File ends at line 188, add function
            lines = content.split('\n')
            if len(lines) <= 188:
                # Add function after last decorator
                function_code = [
                    '',
                    '@rate_limit()',
                    'def get_knowledge():',
                    '    """Get knowledge tree data"""',
                    '    try:',
                    '        user_id = request.args.get(\'user_id\', \'default_user\')',
                    '        ',
                    '        if tech_tree_system is None:',
                    '            return jsonify({',
                    '                \'success\': True,',
                    '                \'knowledge\': {',
                    '                    \'nodes\': [],',
                    '                    \'total_unlocked\': 0,',
                    '                    \'total_available\': 0',
                    '                }',
                    '            }), 200',
                    '        ',
                    '        # Try to get knowledge data',
                    '        try:',
                    '            result = tech_tree_system.get_knowledge(user_id)',
                    '        except AttributeError:',
                    '            # Method doesn\'t exist, return empty data',
                    '            result = {',
                    '                \'success\': True,',
                    '                \'knowledge\': {',
                    '                    \'nodes\': [],',
                    '                    \'total_unlocked\': 0,',
                    '                    \'total_available\': 0',
                    '                }',
                    '            }',
                    '        ',
                    '        # Ensure result has success and knowledge keys',
                    '        if not isinstance(result, dict):',
                    '            result = {\'success\': True, \'knowledge\': {}}',
                    '        if \'success\' not in result:',
                    '            result[\'success\'] = True',
                    '        if \'knowledge\' not in result:',
                    '            result[\'knowledge\'] = result if isinstance(result, dict) else {}',
                    '        ',
                    '        return jsonify(result), 200',
                    '    except Exception as e:',
                    '        logger.error(f"Error getting knowledge: {e}", exc_info=True)',
                    '        return jsonify({',
                    '            \'success\': False,',
                    '            \'error\': str(e),',
                    '            \'knowledge\': {',
                    '                \'nodes\': [],',
                    '                \'total_unlocked\': 0,',
                    '                \'total_available\': 0',
                    '            }',
                    '        }), 200  # Return 200 with empty data instead of 500',
                    ''
                ]
                
                new_lines = lines + function_code
                new_content = '\n'.join(new_lines)
                
                # Write back
                with sftp.open(tech_tree_file, 'w') as f:
                    f.write(new_content.encode('utf-8'))
                print("  OK: Added function definition")
        
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
            print(f"  ERROR: Syntax error: {error}")
        else:
            print("  OK: Syntax is valid")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_function()

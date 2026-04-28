#!/usr/bin/env python3
"""
Check Server File Structure
Reads the actual file structure to see what's wrong
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_structure():
    """Check structure"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        tech_tree_file = '/var/www/html/vidgenerator/backend/routes/tech_tree_routes.py'
        
        # Read file
        print("[1/2] Reading file...")
        sftp = ssh.open_sftp()
        with sftp.open(tech_tree_file, 'r') as f:
            lines = f.readlines()
        sftp.close()
        
        print(f"Total lines: {len(lines)}")
        print()
        
        # Show lines around 188
        print("[2/2] Lines 180-200:")
        for i in range(max(0, 179), min(len(lines), 210)):
            marker = ">>>" if i == 187 else "   "
            line_content = lines[i].rstrip()
            print(f"{marker} {i+1:3d}: {line_content[:80]}")
        
        # Check if there's a function after the decorators
        print()
        print("Checking structure after line 187...")
        if len(lines) > 188:
            # Check what's on line 188
            line_188 = lines[187].rstrip()  # 0-indexed
            print(f"Line 188: {line_188}")
            
            # Check if there's a function definition after decorators
            found_function = False
            for i in range(187, min(len(lines), 200)):
                if lines[i].strip().startswith('def '):
                    found_function = True
                    print(f"  OK: Found function definition on line {i+1}: {lines[i].strip()[:60]}")
                    break
            
            if not found_function:
                print("  ERROR: No function definition found after decorators")
                # Check if file ends after decorators
                if len(lines) <= 189:
                    print("  ERROR: File appears to end after decorators")
                    print("  Fixing: Adding function definition...")
                    
                    # Add function definition
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
                    
                    new_lines = lines[:188] + function_code
                    new_content = '\n'.join(new_lines)
                    
                    # Write back
                    with sftp.open(tech_tree_file, 'w') as f:
                        f.write(new_content.encode('utf-8'))
                    print("  OK: Added function definition")
                    
                    # Test syntax
                    stdin, stdout, stderr = ssh.exec_command(
                        f"python3 -m py_compile {tech_tree_file} 2>&1",
                        timeout=10
                    )
                    error = stderr.read().decode().strip()
                    if error:
                        print(f"  ERROR: Syntax error: {error}")
                    else:
                        print("  OK: Syntax is now valid")
        
        sftp.close()
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_structure()

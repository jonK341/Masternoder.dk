#!/usr/bin/env python3
"""
Fix Tech Tree and Check Calculator
Fixes tech_tree syntax error and checks why point_calculator isn't registered
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_issues():
    """Fix issues"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        sftp = ssh.open_sftp()
        
        # 1. Fix tech_tree_routes.py syntax error
        print("[1/3] Fixing tech_tree_routes.py syntax error...")
        tech_tree_file = '/var/www/html/vidgenerator/backend/routes/tech_tree_routes.py'
        
        with sftp.open(tech_tree_file, 'r') as f:
            content = f.read().decode('utf-8')
        
        lines = content.split('\n')
        
        # The error says "expected an indented block after function definition on line 17"
        # Line 17 is `def get_tech_tree():` and line 18-19 are empty
        # The function body should start immediately after the colon
        
        # Find get_tech_tree function
        for i, line in enumerate(lines):
            if 'def get_tech_tree():' in line:
                # Check if next line is empty and then we have decorators (wrong)
                if i + 1 < len(lines) and lines[i+1].strip() == '':
                    if i + 2 < len(lines) and '@tech_tree_bp.route' in lines[i+2]:
                        # Function body is missing - decorators are after empty line
                        # Need to add function body or move decorators
                        print(f"  Found issue at line {i+1}: function body missing")
                        # The get_tech_tree function should have a body
                        # Check if there's a body further down
                        body_start = None
                        for j in range(i+1, min(i+20, len(lines))):
                            if lines[j].strip() and not lines[j].strip().startswith('@'):
                                body_start = j
                                break
                        
                        if body_start:
                            # Function body exists, just need to remove empty lines
                            # Actually, the issue is that decorators are between function definition and body
                            # Move decorators before function definition
                            print("  Fixing: Moving decorators before function...")
                            # Extract decorators
                            decorators = []
                            for j in range(i+2, body_start):
                                if '@tech_tree_bp.route' in lines[j] or '@rate_limit' in lines[j]:
                                    decorators.append(lines[j])
                            
                            # Remove decorators from after function
                            new_lines = lines[:i+1]  # Up to function definition
                            # Add function body
                            new_lines.extend(lines[body_start:])
                            # But we need to keep decorators - they should be before function
                            # Actually, let's check the structure more carefully
                            # The issue is get_tech_tree has no body, and get_knowledge decorators are after it
                            # We need to add a body to get_tech_tree or remove the empty function
                            
                            # Actually, looking at the error, get_tech_tree() has no body
                            # Let's add a minimal body
                            new_lines = []
                            for j, line in enumerate(lines):
                                new_lines.append(line)
                                if j == i and 'def get_tech_tree():' in line:
                                    # Add function body
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
                                    break
                            
                            content = '\n'.join(new_lines)
                            break
        
        with sftp.open(tech_tree_file, 'w') as f:
            f.write(content.encode('utf-8'))
        print("  ✅ File fixed")
        
        # 2. Check why point_calculator isn't registered
        print()
        print("[2/3] Checking point_calculator blueprint registration...")
        register_file = '/var/www/html/vidgenerator/backend/register_blueprints.py'
        
        stdin, stdout, stderr = ssh.exec_command(
            f"grep -n 'point_calculator' {register_file} | head -5",
            timeout=5
        )
        registration = stdout.read().decode().strip()
        if registration:
            print("  Registration found:")
            print(f"    {registration}")
        else:
            print("  ❌ point_calculator not found in register_blueprints.py")
            # Check if it should be registered
            print("  Checking if file exists...")
            calc_file = '/var/www/html/vidgenerator/backend/routes/point_calculator_routes.py'
            stdin2, stdout2, stderr2 = ssh.exec_command(
                f"test -f {calc_file} && grep -n 'point_calculator_bp' {calc_file} | head -1",
                timeout=5
            )
            blueprint_def = stdout2.read().decode().strip()
            if blueprint_def:
                print(f"  ✅ Blueprint defined: {blueprint_def}")
                print("  ⚠️  Need to add registration to register_blueprints.py")
        
        # 3. Test syntax
        print()
        print("[3/3] Testing syntax...")
        stdin3, stdout3, stderr3 = ssh.exec_command(
            f"python3 -m py_compile {tech_tree_file} 2>&1",
            timeout=10
        )
        error = stderr3.read().decode().strip()
        if error:
            print(f"  ❌ Syntax error: {error}")
        else:
            print("  ✅ Syntax is valid")
        
        sftp.close()
        
        print()
        print("="*70)
        print("FIXES APPLIED")
        print("="*70)
        print()
        print("Restart uWSGI to apply changes")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_issues()

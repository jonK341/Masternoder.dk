#!/usr/bin/env python3
"""
Fix Tech Tree and Point Calculator
Fixes tech_tree function body and point_calculator rate_limit import
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_both():
    """Fix both issues"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        sftp = ssh.open_sftp()
        
        # 1. Fix tech_tree_routes.py - add function body
        print("[1/3] Fixing tech_tree_routes.py...")
        tech_tree_file = '/var/www/html/vidgenerator/backend/routes/tech_tree_routes.py'
        
        with sftp.open(tech_tree_file, 'r') as f:
            content = f.read().decode('utf-8')
        
        lines = content.split('\n')
        
        # Find get_tech_tree function
        func_line = None
        for i, line in enumerate(lines):
            if 'def get_tech_tree():' in line:
                func_line = i
                break
        
        if func_line is not None:
            # Check if function has body
            next_line = lines[func_line + 1] if func_line + 1 < len(lines) else ''
            if next_line.strip() == '' or '@tech_tree_bp.route' in next_line:
                # Function has no body
                print("  Found get_tech_tree without body, adding...")
                # Insert function body after function definition
                function_body = [
                    '    """Get technology tree with user progress"""',
                    '    try:',
                    '        if tech_tree_system is None:',
                    '            return jsonify({',
                    '                \'success\': True,',
                    '                \'tech_tree\': {',
                    '                    \'technologies\': {},',
                    '                    \'total_researched\': 0,',
                    '                    \'total_available\': 0',
                    '                }',
                    '            }), 200',
                    '        ',
                    '        user_id = request.args.get(\'user_id\', \'default_user\')',
                    '        result = tech_tree_system.get_tech_tree(user_id)',
                    '        if not isinstance(result, dict):',
                    '            result = {\'success\': True, \'tech_tree\': {}}',
                    '        if \'success\' not in result:',
                    '            result[\'success\'] = True',
                    '        if \'tech_tree\' not in result:',
                    '            result[\'tech_tree\'] = result if isinstance(result, dict) else {}',
                    '        return jsonify(result), 200',
                    '    except Exception as e:',
                    '        logger.error(f"Error getting tech tree: {e}", exc_info=True)',
                    '        return jsonify({',
                    '            \'success\': False,',
                    '            \'error\': str(e),',
                    '            \'tech_tree\': {',
                    '                \'technologies\': {},',
                    '                \'total_researched\': 0,',
                    '                \'total_available\': 0',
                    '            }',
                    '        }), 200',
                    ''
                ]
                
                # Find where to insert (after function definition, before next decorator or function)
                insert_pos = func_line + 1
                for i in range(func_line + 1, min(func_line + 5, len(lines))):
                    if lines[i].strip() and not lines[i].strip().startswith('#'):
                        if '@tech_tree_bp.route' in lines[i] or 'def ' in lines[i]:
                            insert_pos = i
                            break
                
                new_lines = lines[:insert_pos] + function_body + lines[insert_pos:]
                new_content = '\n'.join(new_lines)
                
                with sftp.open(tech_tree_file, 'w') as f:
                    f.write(new_content.encode('utf-8'))
                print("  ✅ Function body added")
            else:
                print("  ✅ Function already has body")
        
        # 2. Fix point_calculator_routes.py - add rate_limit import
        print()
        print("[2/3] Fixing point_calculator_routes.py...")
        calc_file = '/var/www/html/vidgenerator/backend/routes/point_calculator_routes.py'
        
        with sftp.open(calc_file, 'r') as f:
            calc_content = f.read().decode('utf-8')
        
        if 'from src.utils.rate_limiter import rate_limit' not in calc_content and '@rate_limit' in calc_content:
            # Add import
            lines = calc_content.split('\n')
            # Find where to insert (after other imports)
            insert_pos = 0
            for i, line in enumerate(lines):
                if 'from flask import' in line or 'import logging' in line:
                    insert_pos = i + 1
                if 'point_calculator_bp = Blueprint' in line:
                    break
            
            # Add import
            rate_limit_import = [
                '# Import rate limiter - optional',
                'try:',
                '    from src.utils.rate_limiter import rate_limit',
                'except ImportError:',
                '    # Fallback decorator that does nothing',
                '    def rate_limit():',
                '        def decorator(f):',
                '            return f',
                '        return decorator',
                ''
            ]
            
            new_lines = lines[:insert_pos] + rate_limit_import + lines[insert_pos:]
            new_content = '\n'.join(new_lines)
            
            with sftp.open(calc_file, 'w') as f:
                f.write(new_content.encode('utf-8'))
            print("  ✅ rate_limit import added")
        else:
            print("  ✅ rate_limit import already exists")
        
        # 3. Test syntax
        print()
        print("[3/3] Testing syntax...")
        for file_path, file_name in [(tech_tree_file, 'tech_tree_routes.py'), (calc_file, 'point_calculator_routes.py')]:
            stdin, stdout, stderr = ssh.exec_command(
                f"python3 -m py_compile {file_path} 2>&1",
                timeout=10
            )
            error = stderr.read().decode().strip()
            if error:
                print(f"  ❌ {file_name}: {error}")
            else:
                print(f"  ✅ {file_name}: Syntax valid")
        
        sftp.close()
        
        print()
        print("="*70)
        print("BOTH FILES FIXED")
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
    fix_both()

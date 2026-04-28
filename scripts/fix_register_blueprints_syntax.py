#!/usr/bin/env python3
"""
Fix Register Blueprints Syntax
Fixes the syntax error in register_blueprints.py
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
        
        register_file = '/var/www/html/vidgenerator/backend/register_blueprints.py'
        
        # Read file around line 2336
        print("[1/3] Reading file around line 2336...")
        sftp = ssh.open_sftp()
        with sftp.open(register_file, 'r') as f:
            lines = f.read().decode('utf-8').split('\n')
        sftp.close()
        
        # Show context around line 2336
        print()
        print("Context around line 2336:")
        for i in range(2330, min(2345, len(lines))):
            marker = ">>>" if i == 2335 else "   "
            print(f"{marker} {i+1:4d}: {lines[i]}")
        
        # Find the issue - look for try without except
        print()
        print("[2/3] Finding syntax error...")
        issue_found = False
        for i in range(2330, min(2340, len(lines))):
            if 'try:' in lines[i]:
                # Check if there's an except or finally after
                has_except = False
                for j in range(i+1, min(i+10, len(lines))):
                    if 'except' in lines[j] or 'finally' in lines[j]:
                        has_except = True
                        break
                    if lines[j].strip() and not lines[j].strip().startswith('#') and 'try:' not in lines[j]:
                        # Non-comment, non-try line - might be the issue
                        if 'def ' in lines[j] or '@' in lines[j] or 'class ' in lines[j]:
                            # New definition - no except found
                            print(f"  Found issue: try at line {i+1} has no except/finally")
                            print(f"    Next non-comment line ({j+1}): {lines[j]}")
                            issue_found = True
                            
                            # Fix: Add except block
                            new_lines = lines[:i+1]
                            # Add the code that should be in try
                            # Find what code should be in the try block
                            try_content = []
                            for k in range(i+1, j):
                                if lines[k].strip() and not lines[k].strip().startswith('#'):
                                    try_content.append(lines[k])
                            
                            # Add try content
                            new_lines.extend(try_content)
                            # Add except
                            new_lines.append('    except ImportError as e:')
                            new_lines.append('        _safe_print(f"  [WARN] Could not import: {e}")')
                            new_lines.append('    except Exception as e:')
                            new_lines.append('        _safe_print(f"  [ERROR] Error: {e}")')
                            # Add rest
                            new_lines.extend(lines[j:])
                            
                            lines = new_lines
                            break
                if issue_found:
                    break
        
        if not issue_found:
            # Try a different approach - check the actual structure
            print("  Checking structure more carefully...")
            # Look for the point_calculator registration we added
            for i in range(2330, min(2350, len(lines))):
                if 'point_calculator_bp' in lines[i]:
                    print(f"  Found point_calculator at line {i+1}")
                    # Check structure before and after
                    print("  Structure:")
                    for j in range(max(0, i-5), min(i+10, len(lines))):
                        print(f"    {j+1:4d}: {lines[j]}")
                    
                    # Check if try block is complete
                    try_line = None
                    for j in range(i-10, i):
                        if 'try:' in lines[j]:
                            try_line = j
                            break
                    
                    if try_line:
                        # Check if except exists
                        has_except = False
                        for j in range(try_line+1, min(try_line+20, len(lines))):
                            if 'except' in lines[j]:
                                has_except = True
                                break
                            if j > i+5 and lines[j].strip() and not lines[j].strip().startswith('#'):
                                # Too far, no except
                                break
                        
                        if not has_except:
                            print("  ❌ try block has no except")
                            # Add except after point_calculator registration
                            new_lines = lines[:i+5]  # Up to after app.register_blueprint
                            new_lines.append('    except ImportError as e:')
                            new_lines.append('        _safe_print(f"  [WARN] Could not import point_calculator_routes: {e}")')
                            new_lines.append('    except Exception as e:')
                            new_lines.append('        _safe_print(f"  [ERROR] Error registering point_calculator: {e}")')
                            new_lines.extend(lines[i+5:])
                            lines = new_lines
                            issue_found = True
                            break
        
        if issue_found:
            # Write fixed file
            print()
            print("[3/3] Writing fixed file...")
            new_content = '\n'.join(lines)
            sftp = ssh.open_sftp()
            with sftp.open(register_file, 'w') as f:
                f.write(new_content.encode('utf-8'))
            sftp.close()
            print("  ✅ File fixed")
            
            # Test syntax
            print()
            print("Testing syntax...")
            stdin, stdout, stderr = ssh.exec_command(
                f"python3 -m py_compile {register_file} 2>&1",
                timeout=10
            )
            error = stderr.read().decode().strip()
            if error:
                print(f"  ❌ Syntax error: {error}")
            else:
                print("  ✅ Syntax is valid")
        else:
            print("  ⚠️  Could not automatically fix - manual inspection needed")
        
        sftp.close()
        
        print()
        print("="*70)
        print("SYNTAX FIX ATTEMPTED")
        print("="*70)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_syntax()

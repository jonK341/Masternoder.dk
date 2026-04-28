#!/usr/bin/env python3
"""
Check and Fix Tech Tree Syntax Error
Fixes syntax error on line 188
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
            lines = f.readlines()
        sftp.close()
        
        # Check line 188
        print()
        print("[2/3] Checking line 188...")
        if len(lines) >= 188:
            line_188 = lines[187].rstrip()  # 0-indexed
            print(f"  Line 188: {line_188}")
            
            # Check for common syntax errors
            if line_188.strip() == '' or line_188.strip().startswith('#'):
                print("  ✅ Line is empty or comment")
            elif line_188.count('(') != line_188.count(')'):
                print("  ❌ Mismatched parentheses")
            elif line_188.count('[') != line_188.count(']'):
                print("  ❌ Mismatched brackets")
            elif line_188.count('{') != line_188.count('}'):
                print("  ❌ Mismatched braces")
            else:
                print("  ⚠️  Checking surrounding context...")
                # Show context
                for i in range(max(0, 183), min(len(lines), 193)):
                    marker = ">>>" if i == 187 else "   "
                    print(f"  {marker} {i+1:3d}: {lines[i].rstrip()}")
        else:
            print(f"  ⚠️  File has only {len(lines)} lines")
        
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
            # Try to fix common issues
            if "line 188" in error.lower():
                print("  Attempting to fix...")
                # Read full file
                with sftp.open(tech_tree_file, 'r') as f:
                    content = f.read().decode('utf-8')
                
                # Common fixes
                content_fixed = content
                # Remove stray backslashes
                if '\\' in content[content[:content.find('\n'*187)].rfind('\n'):content.find('\n'*188)]:
                    print("    Removing stray backslash...")
                    lines_list = content.split('\n')
                    if len(lines_list) > 187:
                        lines_list[187] = lines_list[187].replace('\\', '')
                    content_fixed = '\n'.join(lines_list)
                
                # Write back
                if content_fixed != content:
                    with sftp.open(tech_tree_file, 'w') as f:
                        f.write(content_fixed.encode('utf-8'))
                    print("  ✅ Fixed and saved")
                    
                    # Test again
                    stdin2, stdout2, stderr2 = ssh.exec_command(
                        f"python3 -m py_compile {tech_tree_file} 2>&1",
                        timeout=10
                    )
                    error2 = stderr2.read().decode().strip()
                    if error2:
                        print(f"  ❌ Still has error: {error2}")
                    else:
                        print("  ✅ Syntax is now valid")
        else:
            print("  ✅ Syntax is valid")
        
        sftp.close()
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_syntax()

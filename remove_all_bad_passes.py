#!/usr/bin/env python3
"""Remove all incorrectly placed pass statements at module level"""
import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

def main():
    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        file_path = f"{REMOTE_PATH}/src/web/routes/__init__.py"
        
        print("=" * 70)
        print("REMOVING ALL INCORRECTLY PLACED PASS STATEMENTS")
        print("=" * 70)
        
        # Read the file
        sftp = ssh_client.open_sftp()
        with sftp.file(file_path, 'r') as f:
            content = f.read().decode('utf-8', errors='ignore')
        sftp.close()
        
        lines = content.split('\n')
        
        # Remove ALL lines that are just "pass  # Empty except block" 
        # UNLESS they come immediately after an "except" line
        new_lines = []
        removed_count = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Check if this is a "pass  # Empty except block" line
            if stripped == 'pass  # Empty except block':
                # Check if previous non-empty line is an except
                is_after_except = False
                for j in range(i - 1, max(-1, i - 5), -1):
                    if j < 0:
                        break
                    prev_line = lines[j].strip()
                    if prev_line:
                        if 'except' in prev_line and prev_line.endswith(':'):
                            is_after_except = True
                        break
                
                if not is_after_except:
                    print(f"Removing incorrectly placed 'pass' at line {i+1}")
                    removed_count += 1
                    i += 1
                    continue
            
            new_lines.append(line)
            i += 1
        
        print(f"\n✅ Removed {removed_count} incorrectly placed pass statement(s)")
        
        new_content = '\n'.join(new_lines)
        
        if new_content != content:
            # Write back
            sftp = ssh_client.open_sftp()
            with sftp.file(file_path, 'w') as f:
                f.write(new_content.encode('utf-8'))
            sftp.close()
            print("✅ File updated")
        else:
            print("⚠️  No changes made")
        
        # Verify syntax
        print("\nVerifying syntax...")
        stdin, stdout, stderr = ssh_client.exec_command(f"python3 -m py_compile {file_path} 2>&1")
        compile_output = stderr.read().decode('utf-8', errors='ignore')
        if compile_output.strip() and ('SyntaxError' in compile_output or 'IndentationError' in compile_output):
            print(f"❌ Syntax error:\n{compile_output[:400]}")
            # Show first 15 lines
            print("\nFirst 15 lines after cleanup:")
            new_lines_list = new_content.split('\n')
            for k in range(min(15, len(new_lines_list))):
                print(f"{k+1:4d}: {new_lines_list[k][:100]}")
        else:
            print("✅ Syntax is valid!")
            
            # Test import
            print("\nTesting import...")
            stdin, stdout, stderr = ssh_client.exec_command(f"cd {REMOTE_PATH} && python3 -c 'import sys; sys.path.insert(0, \"{REMOTE_PATH}\"); import src.web.routes' 2>&1")
            import_output = stderr.read().decode('utf-8', errors='ignore') + stdout.read().decode('utf-8', errors='ignore')
            if 'SyntaxError' in import_output or 'IndentationError' in import_output:
                print(f"❌ Import still has error:\n{import_output[:400]}")
                
                # Now find and fix actual empty except blocks
                print("\nNow fixing actual empty except blocks...")
                return fix_empty_except_blocks(ssh_client, file_path, new_content)
            else:
                print("✅ Import successful!")
                print("\nRestarting uWSGI...")
                ssh_client.exec_command(f"find {REMOTE_PATH} -type d -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null")
                ssh_client.exec_command(f"find {REMOTE_PATH} -name '*.pyc' -delete 2>/dev/null")
                ssh_client.exec_command("systemctl restart uwsgi")
                import time
                time.sleep(5)
                print("✅ Done")
                return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if ssh_client:
            ssh_client.close()

def fix_empty_except_blocks(ssh_client, file_path, content):
    """Fix empty except blocks properly"""
    try:
        lines = content.split('\n')
        fixed_lines = []
        i = 0
        fixes_made = 0
        
        while i < len(lines):
            line = lines[i]
            fixed_lines.append(line)
            
            # Check if this is an except line
            if 'except' in line and line.strip().endswith(':'):
                except_line_num = i + 1
                except_indent = len(line) - len(line.lstrip())
                
                # Look ahead
                j = i + 1
                found_code = False
                found_pass = False
                
                while j < len(lines) and j < i + 30:
                    check_line = lines[j]
                    check_stripped = check_line.strip()
                    check_indent = len(check_line) - len(check_line.lstrip())
                    
                    # Left the block?
                    if check_stripped and check_indent <= except_indent:
                        if not (check_stripped.startswith('except') or 
                                check_stripped.startswith('finally') or 
                                check_stripped.startswith('else')):
                            break
                    
                    if check_indent > except_indent:
                        if check_stripped == 'pass':
                            found_pass = True
                            break
                        if check_stripped and not check_stripped.startswith('#'):
                            found_code = True
                            break
                    
                    j += 1
                
                if not found_pass and not found_code:
                    indent = ' ' * (except_indent + 4)
                    fixed_lines.append(indent + 'pass  # Empty except block')
                    print(f"✅ Added 'pass' after except at line {except_line_num}")
                    fixes_made += 1
            
            i += 1
        
        new_content = '\n'.join(fixed_lines)
        
        if new_content != content:
            sftp = ssh_client.open_sftp()
            with sftp.file(file_path, 'w') as f:
                f.write(new_content.encode('utf-8'))
            sftp.close()
            print(f"✅ Fixed {fixes_made} empty except block(s)")
        else:
            print("⚠️  No fixes needed")
        
        # Verify
        stdin, stdout, stderr = ssh_client.exec_command(f"python3 -m py_compile {file_path} 2>&1")
        compile_output = stderr.read().decode('utf-8', errors='ignore')
        if compile_output.strip() and ('SyntaxError' in compile_output or 'IndentationError' in compile_output):
            print(f"❌ Still has error:\n{compile_output[:400]}")
            return False
        else:
            print("✅ Syntax valid")
            stdin, stdout, stderr = ssh_client.exec_command(f"cd {REMOTE_PATH} && python3 -c 'import sys; sys.path.insert(0, \"{REMOTE_PATH}\"); import src.web.routes' 2>&1")
            import_output = stderr.read().decode('utf-8', errors='ignore') + stdout.read().decode('utf-8', errors='ignore')
            if 'SyntaxError' in import_output or 'IndentationError' in import_output:
                print(f"❌ Import error:\n{import_output[:400]}")
                return False
            else:
                print("✅ Import successful!")
                REMOTE_PATH = "/var/www/html/vidgenerator"
                ssh_client.exec_command(f"find {REMOTE_PATH} -type d -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null")
                ssh_client.exec_command(f"find {REMOTE_PATH} -name '*.pyc' -delete 2>/dev/null")
                ssh_client.exec_command("systemctl restart uwsgi")
                import time
                time.sleep(5)
                print("✅ Done")
                return True
    except Exception as e:
        print(f"❌ Error in fix_empty_except_blocks: {e}")
        return False

if __name__ == "__main__":
    main()


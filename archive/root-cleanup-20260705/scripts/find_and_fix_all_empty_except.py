#!/usr/bin/env python3
"""Find and fix all empty except blocks"""
import os
import sys
import paramiko
import re

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
        print("FINDING AND FIXING ALL EMPTY EXCEPT BLOCKS")
        print("=" * 70)
        
        # Read the file
        sftp = ssh_client.open_sftp()
        with sftp.file(file_path, 'r') as f:
            content = f.read().decode('utf-8', errors='ignore')
        sftp.close()
        
        lines = content.split('\n')
        fixed_lines = []
        changes_made = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            fixed_lines.append(line)
            
            # Check if this is an except line
            if 'except' in line and line.strip().endswith(':'):
                except_line_num = i + 1
                except_indent = len(line) - len(line.lstrip())
                
                # Look ahead to see what's in the except block
                j = i + 1
                block_content = []
                found_non_comment = False
                found_pass = False
                next_block_end = len(lines)  # Default to end of file
                
                while j < len(lines) and j < i + 50:
                    check_line = lines[j]
                    check_stripped = check_line.strip()
                    check_indent = len(check_line) - len(check_line.lstrip())
                    
                    # If we've left the except block (same or less indent, and not except/finally/else)
                    if check_stripped and check_indent <= except_indent:
                        if not (check_stripped.startswith('except') or 
                                check_stripped.startswith('finally') or 
                                check_stripped.startswith('else') or
                                check_stripped.startswith('elif')):
                            next_block_end = j
                            break
                    
                    # Check if there's a pass statement
                    if check_indent > except_indent and check_stripped == 'pass':
                        found_pass = True
                        break
                    
                    # Check if there's non-comment content
                    if check_indent > except_indent and check_stripped and not check_stripped.startswith('#'):
                        found_non_comment = True
                        break
                    
                    if check_indent > except_indent:
                        block_content.append((j, check_line))
                    
                    j += 1
                
                # If we didn't find pass or non-comment code, the block is empty (or only comments)
                if not found_pass and not found_non_comment and j < next_block_end:
                    # The block is empty - we need to add pass
                    # But first, add any commented lines that were in the block
                    indent = ' ' * (except_indent + 4)
                    
                    # Add all the block content (comments) first
                    for line_idx, comment_line in block_content:
                        fixed_lines.append(comment_line)
                        i += 1
                    
                    # Now add pass
                    fixed_lines.append(indent + 'pass  # Empty except block')
                    changes_made.append(f"Line {except_line_num}: Added 'pass' to empty except block")
                    print(f"✅ Line {except_line_num}: Empty except block - will add 'pass'")
                
                # Skip the lines we already processed
                if block_content:
                    i += len(block_content)
            
            i += 1
        
        new_content = '\n'.join(fixed_lines)
        
        if new_content != content:
            # Write back
            sftp = ssh_client.open_sftp()
            with sftp.file(file_path, 'w') as f:
                f.write(new_content.encode('utf-8'))
            sftp.close()
            print(f"\n✅ File updated with {len(changes_made)} fix(es)")
            for change in changes_made:
                print(f"   - {change}")
        else:
            print("\n⚠️  No changes needed")
        
        # Verify syntax
        print("\nVerifying syntax...")
        stdin, stdout, stderr = ssh_client.exec_command(f"python3 -m py_compile {file_path} 2>&1")
        compile_output = stderr.read().decode('utf-8', errors='ignore')
        if compile_output.strip() and 'SyntaxError' in compile_output:
            print(f"❌ Syntax error still exists:\n{compile_output[:600]}")
            # Show context
            match = re.search(r'line (\d+)', compile_output)
            if match:
                error_line = int(match.group(1))
                print(f"\nContext around line {error_line}:")
                for k in range(max(0, error_line - 5), min(len(fixed_lines), error_line + 5)):
                    marker = ">>>" if k == error_line - 1 else "   "
                    print(f"{marker} {k+1:4d}: {fixed_lines[k][:100]}")
            return False
        else:
            print("✅ Syntax is valid!")
            
            # Clear cache and restart
            print("\nClearing cache and restarting uWSGI...")
            ssh_client.exec_command(f"find {REMOTE_PATH} -type d -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null")
            ssh_client.exec_command(f"find {REMOTE_PATH} -name '*.pyc' -delete 2>/dev/null")
            ssh_client.exec_command("systemctl restart uwsgi")
            import time
            time.sleep(5)
            print("✅ Done - uWSGI restarted")
            return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()


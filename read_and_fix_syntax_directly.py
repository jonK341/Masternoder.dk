#!/usr/bin/env python3
"""Read file and fix syntax error directly"""
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
        
        # Read the file
        sftp = ssh_client.open_sftp()
        with sftp.file(file_path, 'r') as f:
            content = f.read().decode('utf-8', errors='ignore')
        sftp.close()
        
        lines = content.split('\n')
        
        # Show lines 525-535
        print("Lines 525-535:")
        for i in range(524, min(535, len(lines))):
            print(f"{i+1:4}: {repr(lines[i])}")
        
        # The issue: line 528 is "except Exception as e:" and line 529 is a commented print
        # Then line 530 is "import traceback" - but Python needs at least one statement before import
        # We need to add "pass" after the commented print, before import
        
        # Find all except blocks that have only commented prints followed by import/traceback
        fixed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            fixed_lines.append(line)
            
            # Check if this is an except line
            if 'except' in line and line.strip().endswith(':'):
                except_indent = len(line) - len(line.lstrip())
                j = i + 1
                commented_prints = []
                found_import_or_traceback = False
                
                # Look ahead
                while j < len(lines) and j < i + 10:
                    next_line = lines[j]
                    next_indent = len(next_line) - len(next_line.lstrip())
                    
                    # Check if we've left the block
                    if next_line.strip() and next_indent <= except_indent:
                        if not (next_line.strip().startswith('except') or next_line.strip().startswith('finally') or next_line.strip().startswith('else')):
                            break
                    
                    # Check for commented prints
                    if next_line.strip().startswith('#') and 'print' in next_line and 'Disabled to prevent errno 11' in next_line:
                        commented_prints.append((j, next_line))
                    
                    # Check for import or traceback
                    if next_indent > except_indent and (next_line.strip().startswith('import ') or next_line.strip().startswith('traceback')):
                        found_import_or_traceback = True
                        # Check if there's a pass before it
                        has_pass = False
                        for k in range(i+1, j):
                            check_line = lines[k]
                            check_indent = len(check_line) - len(check_line.lstrip())
                            if check_indent > except_indent and check_line.strip() == 'pass':
                                has_pass = True
                                break
                        
                        if not has_pass and commented_prints:
                            # We need to add pass before the import/traceback
                            # Insert pass after the last commented print
                            last_print_line_num = commented_prints[-1][0]
                            indent = ' ' * (except_indent + 4)
                            # We'll add it after we process this line
                            # Actually, we need to add it before j, so let's mark it
                            pass_line_to_add = (last_print_line_num + 1, indent + 'pass  # Empty except block')
                            # Add all lines up to j, then insert pass, then continue
                            for k in range(i+1, j):
                                fixed_lines.append(lines[k])
                                if k == last_print_line_num:
                                    fixed_lines.append(pass_line_to_add[1])
                            i = j
                            continue
                    
                    j += 1
            
            i += 1
        
        # Actually, simpler approach: just find except blocks and add pass where needed
        # Let's use a simpler pattern matching approach
        content_lines = content.split('\n')
        new_lines = []
        i = 0
        
        while i < len(content_lines):
            line = content_lines[i]
            new_lines.append(line)
            
            # If this is an except line
            if 'except' in line and line.strip().endswith(':'):
                except_indent = len(line) - len(line.lstrip())
                
                # Look at the next line
                if i + 1 < len(content_lines):
                    next_line = content_lines[i+1]
                    next_indent = len(next_line) - len(next_line.lstrip())
                    
                    # If next line is a commented print with our marker
                    if next_line.strip().startswith('#') and 'print' in next_line and 'Disabled to prevent errno 11' in next_line and next_indent > except_indent:
                        # Look for the next non-comment line
                        k = i + 2
                        found_non_comment = False
                        while k < len(content_lines) and k < i + 15:
                            check_line = content_lines[k]
                            check_indent = len(check_line) - len(check_line.lstrip())
                            
                            # If we've left the block
                            if check_line.strip() and check_indent <= except_indent:
                                break
                            
                            # If it's a non-comment (not starting with #)
                            if check_line.strip() and not check_line.strip().startswith('#'):
                                found_non_comment = True
                                # If it's import or traceback and there's no pass before it
                                if check_line.strip().startswith('import ') or check_line.strip().startswith('traceback'):
                                    # Check if there's a pass between next_line and check_line
                                    has_pass_between = False
                                    for m in range(i+2, k):
                                        between_line = content_lines[m]
                                        between_indent = len(between_line) - len(between_line.lstrip())
                                        if between_indent > except_indent and between_line.strip() == 'pass':
                                            has_pass_between = True
                                            break
                                    
                                    if not has_pass_between:
                                        # Add pass after next_line (before import/traceback)
                                        indent = ' ' * (except_indent + 4)
                                        # Insert after we've added next_line
                                        # We'll handle this in the next iteration
                                        pass
                                break
                            k += 1
            
            i += 1
        
        # Actually, let's just do it with a simple replacement on the content string
        # Pattern: except ...:\n    # print(...)\n    import
        import re
        
        # More specific pattern
        pattern = r'(except[^\n]+:\n)((\s+#[^\n]*print[^\n]*Disabled to prevent errno 11[^\n]*\n)+)(\s+)(import|traceback)'
        
        def add_pass_replacement(match):
            except_part = match.group(1)
            commented_prints = match.group(2)
            indent = match.group(4)
            import_part = match.group(5)
            return except_part + commented_prints + indent + 'pass  # Empty except block\n' + indent + import_part
        
        new_content = re.sub(pattern, add_pass_replacement, content, flags=re.MULTILINE)
        
        if new_content != content:
            # Write back
            sftp = ssh_client.open_sftp()
            with sftp.file(file_path, 'w') as f:
                f.write(new_content)
            sftp.close()
            print("✅ Fixed using pattern replacement")
        else:
            print("⚠️  Pattern didn't match, need manual fix")
            # Show the exact problematic section
            print("\nProblematic section (lines 528-532):")
            for idx in range(527, min(532, len(content_lines))):
                print(f"{idx+1:4}: {content_lines[idx]}")
            return False
        
        # Verify
        stdin, stdout, stderr = ssh_client.exec_command(f"python3 -m py_compile {file_path} 2>&1")
        compile_output = stderr.read().decode('utf-8', errors='ignore')
        if compile_output.strip():
            print(f"❌ Still has errors: {compile_output[:300]}")
            return False
        else:
            print("✅ Syntax is valid")
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


#!/usr/bin/env python3
"""Simple test of import to get syntax error"""
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
        
        print("=" * 70)
        print("TESTING IMPORT TO FIND SYNTAX ERROR")
        print("=" * 70)
        
        # Create a test script on the server
        test_script = f"""{REMOTE_PATH}/test_import.py"""
        script_content = f"""import sys
sys.path.insert(0, '{REMOTE_PATH}')

try:
    import src.web.routes
except SyntaxError as syntax_err:
    print("LINE_NUM:" + str(syntax_err.lineno))
    print("MSG:" + str(syntax_err.msg))
    if syntax_err.text:
        print("TEXT:" + syntax_err.text.rstrip())
    import traceback
    traceback.print_exc()
except Exception as other_err:
    print("OTHER:" + str(type(other_err).__name__) + ":" + str(other_err))
    import traceback
    traceback.print_exc()
"""
        
        # Write test script
        sftp = ssh_client.open_sftp()
        with sftp.file(test_script, 'w') as f:
            f.write(script_content.encode('utf-8'))
        sftp.close()
        
        # Run it
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {REMOTE_PATH} && python3 test_import.py 2>&1")
        output = stdout.read().decode('utf-8', errors='ignore')
        error_output = stderr.read().decode('utf-8', errors='ignore')
        
        full_output = output + error_output
        print("\nImport test output:")
        print(full_output)
        
        # Parse error line
        error_line = None
        for line in full_output.split('\n'):
            if line.startswith('LINE_NUM:'):
                error_line = int(line.split(':', 1)[1])
                break
            # Also check traceback format
            if 'File' in line and '__init__.py' in line and 'line' in line:
                parts = line.split('line')
                if len(parts) > 1:
                    try:
                        error_line = int(parts[1].split()[0])
                        break
                    except:
                        pass
        
        if error_line:
            print(f"\n🔍 Syntax error at line {error_line}")
            
            # Read and fix
            file_path = f"{REMOTE_PATH}/src/web/routes/__init__.py"
            sftp = ssh_client.open_sftp()
            with sftp.file(file_path, 'r') as f:
                content = f.read().decode('utf-8', errors='ignore')
            sftp.close()
            
            lines = content.split('\n')
            
            print(f"\nContext around line {error_line}:")
            for i in range(max(0, error_line - 6), min(len(lines), error_line + 4)):
                marker = ">>>" if i == error_line - 1 else "   "
                print(f"{marker} {i+1:4d}: {lines[i]}")
            
            # Fix: if line error_line-1 is except, add pass after it
            if error_line - 1 < len(lines):
                target_idx = error_line - 1
                target_line = lines[target_idx]
                
                if 'except' in target_line and target_line.strip().endswith(':'):
                    except_indent = len(target_line) - len(target_line.lstrip())
                    
                    # Check if next line needs pass
                    needs_pass = False
                    if target_idx + 1 >= len(lines):
                        needs_pass = True
                    else:
                        next_line = lines[target_idx + 1]
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if not next_line.strip() or (next_line.strip() and next_indent <= except_indent):
                            needs_pass = True
                        elif next_line.strip().startswith('#') and target_idx + 2 >= len(lines):
                            needs_pass = True
                        elif next_line.strip().startswith('#'):
                            # Check if line after comment needs pass
                            if target_idx + 2 < len(lines):
                                after_comment = lines[target_idx + 2]
                                after_indent = len(after_comment) - len(after_comment.lstrip())
                                if after_indent <= except_indent:
                                    needs_pass = True
                            else:
                                needs_pass = True
                    
                    if needs_pass:
                        indent = ' ' * (except_indent + 4)
                        # Insert pass after except line (or after comment if next line is comment)
                        insert_idx = target_idx + 1
                        if insert_idx < len(lines) and lines[insert_idx].strip().startswith('#'):
                            # Skip comment, insert after it
                            insert_idx = target_idx + 2
                        
                        lines.insert(insert_idx, indent + 'pass  # Empty except block')
                        print(f"\n✅ Adding 'pass' after line {target_idx + 1}")
                        
                        # Write back
                        new_content = '\n'.join(lines)
                        sftp = ssh_client.open_sftp()
                        with sftp.file(file_path, 'w') as f:
                            f.write(new_content.encode('utf-8'))
                        sftp.close()
                        print("✅ File updated")
                        
                        # Verify and restart
                        stdin, stdout, stderr = ssh_client.exec_command(f"python3 -m py_compile {file_path} 2>&1")
                        compile_output = stderr.read().decode('utf-8', errors='ignore')
                        if compile_output.strip() and 'SyntaxError' in compile_output:
                            print(f"❌ Still has error: {compile_output[:400]}")
                        else:
                            print("✅ Syntax verified")
                            
                            print("\nRestarting uWSGI...")
                            ssh_client.exec_command(f"find {REMOTE_PATH} -type d -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null")
                            ssh_client.exec_command(f"find {REMOTE_PATH} -name '*.pyc' -delete 2>/dev/null")
                            ssh_client.exec_command("systemctl restart uwsgi")
                            import time
                            time.sleep(5)
                            print("✅ Done")
        
        # Clean up test script
        try:
            sftp = ssh_client.open_sftp()
            sftp.remove(test_script)
            sftp.close()
        except:
            pass
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()


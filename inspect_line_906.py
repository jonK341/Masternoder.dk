#!/usr/bin/env python3
"""Inspect code around line 906"""
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
        
        print("Context around line 906:")
        for i in range(max(0, 900), min(len(lines), 915)):
            marker = ">>>" if i in [905, 907] else "   "
            print(f"{marker} {i+1:4d}: {lines[i]}")
        
        # Check line 906 (index 905)
        if 905 < len(lines):
            if_line = lines[905]
            if_indent = len(if_line) - len(if_line.lstrip())
            print(f"\nLine 906 indent: {if_indent}")
            print(f"Line 906 content: {repr(if_line)}")
            
            # Check what's after the if
            if 906 < len(lines):
                next_line = lines[906]
                next_indent = len(next_line) - len(next_line.lstrip())
                print(f"Line 907 indent: {next_indent}")
                print(f"Line 907 content: {repr(next_line)}")
                
                # If next line is else at same indent, the if block is empty
                if next_line.strip().startswith('else:') and next_indent == if_indent:
                    print("\n⚠️  If block is empty - need to add pass before else")
                    # Insert pass after if
                    indent = ' ' * (if_indent + 4)
                    lines.insert(906, indent + 'pass  # Empty if block')
                    
                    # Write back
                    new_content = '\n'.join(lines)
                    sftp = ssh_client.open_sftp()
                    with sftp.file(file_path, 'w') as f:
                        f.write(new_content.encode('utf-8'))
                    sftp.close()
                    print("✅ Added 'pass' to empty if block")
                    
                    # Verify
                    stdin, stdout, stderr = ssh_client.exec_command(f"python3 -m py_compile {file_path} 2>&1")
                    compile_output = stderr.read().decode('utf-8', errors='ignore')
                    if compile_output.strip() and ('SyntaxError' in compile_output or 'IndentationError' in compile_output):
                        print(f"❌ Still has error:\n{compile_output[:400]}")
                    else:
                        print("✅ Syntax valid")
                        stdin, stdout, stderr = ssh_client.exec_command(f"cd {REMOTE_PATH} && python3 -c 'import sys; sys.path.insert(0, \"{REMOTE_PATH}\"); import src.web.routes' 2>&1")
                        import_output = stderr.read().decode('utf-8', errors='ignore') + stdout.read().decode('utf-8', errors='ignore')
                        if 'SyntaxError' in import_output or 'IndentationError' in import_output:
                            print(f"❌ Import error:\n{import_output[:400]}")
                        else:
                            print("✅ Import successful!")
                            ssh_client.exec_command(f"find {REMOTE_PATH} -type d -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null")
                            ssh_client.exec_command(f"find {REMOTE_PATH} -name '*.pyc' -delete 2>/dev/null")
                            ssh_client.exec_command("systemctl restart uwsgi")
                            import time
                            time.sleep(5)
                            print("✅ Done")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()


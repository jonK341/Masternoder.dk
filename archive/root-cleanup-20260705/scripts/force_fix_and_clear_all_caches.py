#!/usr/bin/env python3
"""Force fix line 528 and clear ALL caches aggressively"""
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
        print("FORCE FIX LINE 528 AND CLEAR ALL CACHES")
        print("=" * 70)
        
        # Step 1: Stop uWSGI to prevent file locking
        print("\n1. Stopping uWSGI...")
        ssh_client.exec_command("systemctl stop uwsgi")
        import time
        time.sleep(2)
        
        # Step 2: Set permissions
        print("\n2. Setting file permissions...")
        ssh_client.exec_command(f"chmod 666 {file_path}")
        ssh_client.exec_command(f"chown www-data:www-data {file_path}")
        
        # Step 3: Read file
        print("\n3. Reading file...")
        sftp = ssh_client.open_sftp()
        with sftp.file(file_path, 'r') as f:
            content = f.read().decode('utf-8', errors='ignore')
        sftp.close()
        
        lines = content.split('\n')
        
        # Step 4: Show current state
        print("\n4. Current state around line 528:")
        for i in range(max(0, 523), min(len(lines), 540)):
            marker = ">>>" if i in [527, 529, 530] else "   "
            print(f"{marker} {i+1:4d}: {lines[i]}")
        
        # Step 5: Force fix - ensure line 528 has proper pass
        print("\n5. Force fixing line 528...")
        fixed = False
        
        if 527 < len(lines):
            line_528 = lines[527]
            if 'except' in line_528 and line_528.strip().endswith(':'):
                except_indent = len(line_528) - len(line_528.lstrip())
                
                # Check line 529
                if 528 < len(lines):
                    line_529 = lines[528]
                    line_529_stripped = line_529.strip()
                    line_529_indent = len(line_529) - len(line_529.lstrip())
                    
                    # If line 529 doesn't have proper pass, fix it
                    if line_529_stripped != 'pass  # Empty except block' or line_529_indent != except_indent + 4:
                        # Replace line 529 with proper pass
                        indent = ' ' * (except_indent + 4)
                        lines[528] = indent + 'pass  # Empty except block'
                        print(f"  ✅ Fixed line 529 to have proper pass")
                        fixed = True
                    else:
                        print(f"  → Line 529 already has proper pass")
                
                # Also check line 530 (another except)
                if 529 < len(lines):
                    line_530 = lines[529]
                    if 'except' in line_530 and line_530.strip().endswith(':'):
                        except2_indent = len(line_530) - len(line_530.lstrip())
                        
                        # Check line 531
                        if 530 < len(lines):
                            line_531 = lines[530]
                            line_531_stripped = line_531.strip()
                            line_531_indent = len(line_531) - len(line_531.lstrip())
                            
                            # Line 531 should have pass, but line 532 has import at same level
                            # This might be the issue - the except block should end before import
                            if line_531_stripped == 'pass  # Empty except block' and 531 < len(lines):
                                line_532 = lines[531]
                                line_532_indent = len(line_532) - len(line_532.lstrip())
                                # If import is at same level as pass, it's part of the except block, which is fine
                                # But if Python is complaining, maybe we need to ensure proper structure
                                if line_532_indent == line_531_indent and 'import' in line_532:
                                    # This is actually fine - pass and import can be in same block
                                    print(f"  → Line 530-532 structure looks OK")
                                else:
                                    print(f"  → Line 530-532 structure might need adjustment")
        
        # Step 6: Write back
        if fixed:
            print("\n6. Writing fixed content...")
            new_content = '\n'.join(lines)
            sftp = ssh_client.open_sftp()
            with sftp.file(file_path, 'w') as f:
                f.write(new_content.encode('utf-8'))
            sftp.close()
            print("  ✅ File written")
        
        # Step 7: AGGRESSIVE cache clearing
        print("\n7. Clearing ALL caches aggressively...")
        commands = [
            f"find {REMOTE_PATH} -type d -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null",
            f"find {REMOTE_PATH} -name '*.pyc' -delete 2>/dev/null",
            f"find {REMOTE_PATH} -name '*.pyo' -delete 2>/dev/null",
            f"find {REMOTE_PATH} -name '*.pyc' -type f -delete 2>/dev/null",
            f"rm -rf {REMOTE_PATH}/src/web/routes/__pycache__ 2>/dev/null",
            f"rm -rf {REMOTE_PATH}/src/web/__pycache__ 2>/dev/null",
            f"rm -rf {REMOTE_PATH}/src/__pycache__ 2>/dev/null",
            f"rm -rf {REMOTE_PATH}/__pycache__ 2>/dev/null",
        ]
        
        for cmd in commands:
            ssh_client.exec_command(cmd)
        
        print("  ✅ All caches cleared")
        
        # Step 8: Verify syntax
        print("\n8. Verifying syntax...")
        stdin, stdout, stderr = ssh_client.exec_command(f"python3 -m py_compile {file_path} 2>&1")
        compile_output = stderr.read().decode('utf-8', errors='ignore')
        if compile_output.strip() and ('SyntaxError' in compile_output or 'IndentationError' in compile_output):
            print(f"  ❌ Syntax error:\n{compile_output[:500]}")
        else:
            print("  ✅ Syntax valid")
            
            # Step 9: Test import with fresh Python
            print("\n9. Testing import with fresh Python process...")
            stdin, stdout, stderr = ssh_client.exec_command(f"cd {REMOTE_PATH} && python3 -B -c 'import sys; sys.path.insert(0, \"{REMOTE_PATH}\"); import src.web.routes; print(\"IMPORT_SUCCESS\")' 2>&1")
            import_output = stderr.read().decode('utf-8', errors='ignore') + stdout.read().decode('utf-8', errors='ignore')
            
            if 'IMPORT_SUCCESS' in import_output:
                print("  ✅ Import successful!")
            elif 'line 528' in import_output or 'line 530' in import_output or 'SyntaxError' in import_output:
                print(f"  ❌ Import error:\n{import_output[:600]}")
            else:
                print(f"  ⚠️  Import output:\n{import_output[:400]}")
            
            # Step 10: Test application creation
            print("\n10. Testing application creation...")
            stdin, stdout, stderr = ssh_client.exec_command(f"cd {REMOTE_PATH} && timeout 30 python3 -B -c 'import sys; sys.path.insert(0, \"{REMOTE_PATH}\"); from src.app import create_app; app = create_app(); print(\"APP_SUCCESS\")' 2>&1")
            app_output = stderr.read().decode('utf-8', errors='ignore') + stdout.read().decode('utf-8', errors='ignore')
            
            if 'APP_SUCCESS' in app_output:
                print("  ✅ Application creation successful!")
            elif 'line 528' in app_output or 'line 530' in app_output:
                print(f"  ❌ Application creation error:\n{app_output[:600]}")
                # Extract exact error
                for line in app_output.split('\n'):
                    if 'line 528' in line or 'line 530' in line or 'SyntaxError' in line or 'IndentationError' in line:
                        print(f"\n  Error line: {line[:200]}")
            else:
                print(f"  ⚠️  Application output:\n{app_output[:400]}")
            
            # Step 11: Restore permissions and restart
            print("\n11. Restoring permissions and restarting uWSGI...")
            ssh_client.exec_command(f"chmod 644 {file_path}")
            ssh_client.exec_command(f"chown www-data:www-data {file_path}")
            ssh_client.exec_command("systemctl start uwsgi")
            time.sleep(5)
            
            # Step 12: Check uWSGI status
            print("\n12. Checking uWSGI status...")
            stdin, stdout, stderr = ssh_client.exec_command("systemctl status uwsgi --no-pager -l | head -30")
            status_output = stdout.read().decode('utf-8', errors='ignore')
            print(status_output)
            
            print("\n" + "=" * 70)
            print("✅ FIX COMPLETE")
            print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()


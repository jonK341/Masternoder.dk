#!/usr/bin/env python3
"""
Fix Tech Tree Orphaned Code
Removes orphaned code after get_knowledge function
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_orphaned_code():
    """Fix orphaned code"""
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
        
        # Find get_knowledge function end
        print()
        print("[2/3] Finding and fixing orphaned code...")
        func_end = None
        for i, line in enumerate(lines):
            if 'def get_knowledge' in line:
                # Find the end of the function (next function or route decorator)
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith('@tech_tree_bp.route') or lines[j].strip().startswith('def '):
                        func_end = j
                        break
                break
        
        if func_end is None:
            print("  ❌ Could not find function end")
        else:
            # Check for orphaned code (code without def statement)
            orphaned_start = None
            for i in range(func_end, min(len(lines), func_end + 20)):
                if '"""Get technology tree with user progress"""' in lines[i]:
                    orphaned_start = i
                    break
            
            if orphaned_start:
                print(f"  ✅ Found orphaned code starting at line {orphaned_start + 1}")
                # Find where it ends (next route decorator)
                orphaned_end = None
                for i in range(orphaned_start, len(lines)):
                    if lines[i].strip().startswith('@tech_tree_bp.route'):
                        orphaned_end = i
                        break
                
                if orphaned_end:
                    print(f"  ✅ Orphaned code ends at line {orphaned_end}")
                    # Remove orphaned code
                    new_lines = lines[:orphaned_start] + lines[orphaned_end:]
                    
                    # Write back
                    with sftp.open(tech_tree_file, 'w') as f:
                        f.write(''.join(new_lines).encode('utf-8'))
                    print(f"  ✅ Removed {orphaned_end - orphaned_start} lines of orphaned code")
                else:
                    print("  ⚠️  Could not find end of orphaned code")
            else:
                print("  ✅ No orphaned code found")
        
        sftp.close()
        
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
        else:
            print("  ✅ Syntax is valid")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_orphaned_code()

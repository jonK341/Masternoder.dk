#!/usr/bin/env python3
"""
Fix Duplicate Except Blocks
Removes duplicate except blocks in register_blueprints.py
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_duplicates():
    """Fix duplicate except blocks"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        register_file = '/var/www/html/vidgenerator/backend/register_blueprints.py'
        
        # Read file
        print("[1/3] Reading file...")
        sftp = ssh.open_sftp()
        with sftp.open(register_file, 'r') as f:
            lines = f.read().decode('utf-8').split('\n')
        sftp.close()
        print(f"  [OK] Read {len(lines)} lines")
        
        # Find and fix duplicate except blocks around line 2345
        print()
        print("[2/3] Finding duplicate except blocks...")
        print("Lines 2335-2350:")
        for i in range(2334, min(2350, len(lines))):
            print(f"  {i+1:4d}: {lines[i]}")
        
        # The issue: line 2345 has `except ImportError` which is duplicate
        # Remove lines 2345-2347 (duplicate except blocks)
        new_lines = []
        skip_next = False
        for i, line in enumerate(lines):
            if i == 2344:  # Line 2345 (0-indexed: 2344)
                # Check if this is a duplicate except
                if 'except ImportError' in line and i > 2340:
                    # Check if previous except was for point_calculator
                    if 'point_calculator' in '\n'.join(lines[max(0, i-10):i]):
                        print(f"  Found duplicate except at line {i+1}, removing...")
                        skip_next = True
                        continue
            if skip_next and ('except' in line or 'Error registering point_analytics' in line):
                # Skip duplicate except blocks
                if i < 2348:  # Only skip a few lines
                    continue
                else:
                    skip_next = False
            
            new_lines.append(line)
        
        # Write fixed file
        print()
        print("[3/3] Writing fixed file...")
        new_content = '\n'.join(new_lines)
        sftp = ssh.open_sftp()
        with sftp.open(register_file, 'w') as f:
            f.write(new_content.encode('utf-8'))
        sftp.close()
        print("  ✅ File written")
        
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
        
        # Show fixed section
        print()
        print("Fixed section (lines 2335-2350):")
        new_lines_list = new_content.split('\n')
        for i in range(2334, min(2350, len(new_lines_list))):
            print(f"  {i+1:4d}: {new_lines_list[i]}")
        
        sftp.close()
        
        print()
        print("="*70)
        print("DUPLICATE EXCEPT BLOCKS REMOVED")
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
    fix_duplicates()

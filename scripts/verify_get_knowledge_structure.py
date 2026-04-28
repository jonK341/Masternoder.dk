#!/usr/bin/env python3
"""
Verify get_knowledge Function Structure
Checks the exact structure of the get_knowledge function on the server
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def verify_structure():
    """Verify structure"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        tech_tree_file = '/var/www/html/vidgenerator/backend/routes/tech_tree_routes.py'
        
        # Read file
        print("[1/2] Reading file...")
        sftp = ssh.open_sftp()
        with sftp.open(tech_tree_file, 'r') as f:
            lines = f.readlines()
        sftp.close()
        
        print(f"Total lines: {len(lines)}")
        print()
        
        # Find get_knowledge function
        print("[2/2] Finding get_knowledge function...")
        func_start = None
        for i, line in enumerate(lines):
            if 'def get_knowledge' in line:
                func_start = i
                break
        
        if func_start is None:
            print("  ❌ get_knowledge function NOT found")
        else:
            print(f"  ✅ Found at line {func_start + 1}")
            print()
            print("  Function context (10 lines before, 50 lines after):")
            for i in range(max(0, func_start - 10), min(len(lines), func_start + 50)):
                marker = ">>>" if i == func_start else "   "
                print(f"  {marker} {i+1:3d}: {lines[i].rstrip()}")
        
        # Check for decorators before function
        if func_start:
            print()
            print("  Checking decorators...")
            decorator_count = 0
            for i in range(max(0, func_start - 5), func_start):
                if '@' in lines[i] and ('route' in lines[i] or 'rate_limit' in lines[i]):
                    decorator_count += 1
                    print(f"    Line {i+1}: {lines[i].strip()}")
            if decorator_count == 0:
                print("  ❌ No decorators found before function")
            elif decorator_count < 3:
                print(f"  ⚠️  Only {decorator_count} decorator(s) found (expected 3)")
        
        sftp.close()
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_structure()

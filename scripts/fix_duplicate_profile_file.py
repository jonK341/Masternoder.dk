#!/usr/bin/env python3
"""
Fix Duplicate Profile File
Copy the correct file to the location Flask is reading from
"""
import paramiko
import os

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def fix_duplicate():
    """Fix duplicate profile file"""
    print("=" * 70)
    print("FIXING DUPLICATE PROFILE FILE")
    print("=" * 70)
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        # Copy correct file to Flask's path
        correct_file = '/var/www/html/vidgenerator/profile/index.html'
        flask_file = '/var/www/html/vidgenerator/vidgenerator/profile/index.html'
        
        print(f"Copying from: {correct_file}")
        print(f"To: {flask_file}")
        print()
        
        # Ensure directory exists
        ssh.exec_command(f"mkdir -p /var/www/html/vidgenerator/vidgenerator/profile", timeout=10)
        
        # Copy file
        cmd = f"cp {correct_file} {flask_file}"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("  [OK] File copied")
        else:
            error = stderr.read().decode('utf-8')
            print(f"  [FAIL] Copy failed: {error}")
            return
        
        # Verify
        cmd2 = f"grep -c 'loadPointsStats' {flask_file} 2>/dev/null || echo '0'"
        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=10)
        has_method = stdout2.read().decode('utf-8').strip()
        
        if has_method != '0':
            print("  [OK] File verified - has loadPointsStats")
        else:
            print("  [FAIL] File verification failed")
        
        # Get file size
        cmd3 = f"ls -lh {flask_file} | awk '{{print $5}}'"
        stdin3, stdout3, stderr3 = ssh.exec_command(cmd3, timeout=10)
        size = stdout3.read().decode('utf-8').strip()
        print(f"  File size: {size}")
        
        ssh.close()
        
        print("\n" + "=" * 70)
        print("FIX COMPLETE")
        print("=" * 70)
        print("\nPlease restart services and test again.")
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_duplicate()

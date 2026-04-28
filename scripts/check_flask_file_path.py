#!/usr/bin/env python3
"""
Check Flask File Path - Verify what path Flask is using
"""
import paramiko
import os

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def check_paths():
    """Check file paths"""
    print("=" * 70)
    print("CHECKING FLASK FILE PATHS")
    print("=" * 70)
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        # Check possible paths
        paths_to_check = [
            '/var/www/html/vidgenerator/profile/index.html',
            '/var/www/html/vidgenerator/vidgenerator/profile/index.html',
            '/home/ubuntu/vidgenerator/profile/index.html',
        ]
        
        for path in paths_to_check:
            cmd = f"test -f {path} && echo 'EXISTS' && ls -lh {path} | awk '{{print $5}}' || echo 'NOT FOUND'"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            result = stdout.read().decode('utf-8').strip()
            if 'EXISTS' in result:
                size = result.split('\n')[1] if '\n' in result else 'unknown'
                print(f"  [OK] {path}")
                print(f"      Size: {size}")
                
                # Check content
                cmd2 = f"grep -c 'loadPointsStats' {path} 2>/dev/null || echo '0'"
                stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=10)
                has_method = stdout2.read().decode('utf-8').strip()
                print(f"      Has loadPointsStats: {'Yes' if has_method != '0' else 'No'}")
            else:
                print(f"  [MISS] {path}")
        
        # Check what Flask route file says
        print("\nChecking Flask route file...")
        route_file = '/var/www/html/vidgenerator/backend/routes/dashboard_page_routes.py'
        cmd = f"grep -A 5 'profile_path =' {route_file} 2>/dev/null | head -10"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        route_code = stdout.read().decode('utf-8')
        print(f"  Route code:\n{route_code}")
        
        ssh.close()
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_paths()

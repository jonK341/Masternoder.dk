#!/usr/bin/env python3
"""
Fix Route On Server
Adds the missing /api/monetization/top50 route (without hyphen) to the server file
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_route():
    """Fix route on server"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        route_file = "/var/www/html/vidgenerator/backend/routes/monetization_top50_routes.py"
        
        # Read the file
        print("[1/3] Reading file...")
        sftp = ssh.open_sftp()
        with sftp.open(route_file, 'r') as f:
            content = f.read().decode('utf-8')
        sftp.close()
        print(f"  [OK] Read {len(content)} bytes")
        
        # Check if route already exists
        if "@monetization_top50_bp.route('/api/monetization/top50'" in content:
            print()
            print("  [OK] Route /api/monetization/top50 already exists")
            return True
        
        # Find the line with top-50 route and add top50 route before it
        print()
        print("[2/3] Adding missing route...")
        lines = content.split('\n')
        new_lines = []
        added = False
        
        for i, line in enumerate(lines):
            # If we find the top-50 route, add top50 route before it
            if "@monetization_top50_bp.route('/api/monetization/top-50'" in line and not added:
                # Add the top50 route (without hyphen)
                new_lines.append("@monetization_top50_bp.route('/api/monetization/top50', methods=['GET'])")
                new_lines.append("@monetization_top50_bp.route('/vidgenerator/api/monetization/top50', methods=['GET'])")
                added = True
            new_lines.append(line)
        
        if not added:
            print("  [ERROR] Could not find insertion point")
            return False
        
        new_content = '\n'.join(new_lines)
        
        # Write the file
        print()
        print("[3/3] Writing file...")
        sftp = ssh.open_sftp()
        with sftp.open(route_file, 'w') as f:
            f.write(new_content.encode('utf-8'))
        sftp.close()
        print("  [OK] File written")
        
        # Verify
        print()
        print("Verifying route was added...")
        stdin, stdout, stderr = ssh.exec_command(
            f"grep -n '@monetization_top50_bp.route.*top50' {route_file}",
            timeout=5
        )
        routes = stdout.read().decode().strip()
        if routes:
            print("  ✅ Routes found:")
            print(f"    {routes}")
        else:
            print("  ❌ Routes not found")
        
        print()
        print("="*70)
        print("ROUTE FIXED")
        print("="*70)
        print()
        print("Restart uWSGI to apply changes:")
        print("  systemctl restart uwsgi-vidgenerator.service")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_route()

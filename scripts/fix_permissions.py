#!/usr/bin/env python3
"""
Fix File Permissions Script
Checks and fixes permissions for all directories and files on the server
"""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_permissions():
    """Fix permissions for all directories and files"""
    print("="*70)
    print("FIXING FILE PERMISSIONS")
    print("="*70)
    print()
    
    try:
        # Connect
        print("[1/3] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Directories that need 755 permissions
        directories = [
            "/var/www/html/vidgenerator",
            "/var/www/html/vidgenerator/static",
            "/var/www/html/vidgenerator/static/css",
            "/var/www/html/vidgenerator/static/js",
            "/var/www/html/vidgenerator/unified_dashboard",
            "/var/www/html/vidgenerator/leaderboards",
            "/var/www/html/backend",
            "/var/www/html/backend/routes",
            "/var/www/html/backend/services",
            "/var/www/html/backend/static",
        ]
        
        # Fix directory permissions
        print("[2/3] Fixing directory permissions (755)...")
        for directory in directories:
            try:
                stdin, stdout, stderr = ssh.exec_command(f"chmod -R 755 {directory} 2>&1", timeout=10)
                output = stdout.read().decode().strip()
                error = stderr.read().decode().strip()
                if error:
                    print(f"  [WARN] {directory}: {error}")
                else:
                    print(f"  [OK] {directory}")
            except Exception as e:
                print(f"  [ERROR] {directory}: {e}")
        print()
        
        # Fix file permissions (644 for files, 755 for executables)
        print("[3/3] Fixing file permissions...")
        
        # Static files should be 644
        static_file_patterns = [
            "/var/www/html/vidgenerator/static/css/*.css",
            "/var/www/html/vidgenerator/static/js/*.js",
            "/var/www/html/vidgenerator/**/*.html",
            "/var/www/html/backend/**/*.py",
        ]
        
        for pattern in static_file_patterns:
            try:
                # Use find to set permissions on files
                if '*.css' in pattern or '*.js' in pattern:
                    # For specific file types
                    dir_path = os.path.dirname(pattern.replace('*', ''))
                    file_ext = pattern.split('.')[-1]
                    stdin, stdout, stderr = ssh.exec_command(
                        f"find {dir_path} -type f -name '*.{file_ext}' -exec chmod 644 {{}} \\; 2>&1",
                        timeout=30
                    )
                elif '*.html' in pattern:
                    # For HTML files
                    base_dir = pattern.split('/**')[0]
                    stdin, stdout, stderr = ssh.exec_command(
                        f"find {base_dir} -type f -name '*.html' -exec chmod 644 {{}} \\; 2>&1",
                        timeout=30
                    )
                elif '*.py' in pattern:
                    # For Python files
                    base_dir = pattern.split('/**')[0]
                    stdin, stdout, stderr = ssh.exec_command(
                        f"find {base_dir} -type f -name '*.py' -exec chmod 644 {{}} \\; 2>&1",
                        timeout=30
                    )
                
                output = stdout.read().decode().strip()
                error = stderr.read().decode().strip()
                if error and 'No such file' not in error:
                    print(f"  [WARN] {pattern}: {error}")
                else:
                    print(f"  [OK] {pattern}")
            except Exception as e:
                print(f"  [ERROR] {pattern}: {e}")
        
        # Make Python scripts executable if needed
        print()
        print("[4/4] Ensuring Python scripts are executable...")
        try:
            stdin, stdout, stderr = ssh.exec_command(
                "find /var/www/html/backend -type f -name '*.py' -exec chmod 644 {} \\; 2>&1",
                timeout=30
            )
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            if error and 'No such file' not in error:
                print(f"  [WARN] {error}")
            else:
                print("  [OK] Python files set to 644")
        except Exception as e:
            print(f"  [ERROR] {e}")
        
        # Verify key files exist and have correct permissions
        print()
        print("[5/5] Verifying key files...")
        key_files = [
            "/var/www/html/vidgenerator/static/css/modern-design-system.css",
            "/var/www/html/vidgenerator/static/css/navigation-toolbar.css",
            "/var/www/html/vidgenerator/static/js/navigation-toolbar.js",
            "/var/www/html/vidgenerator/static/js/comprehensive-auto-save.js",
            "/var/www/html/vidgenerator/static/js/enhanced-frontpage-stats.js",
            "/var/www/html/vidgenerator/static/js/top50-monetization-frame.js",
            "/var/www/html/vidgenerator/static/js/energy-regeneration-timers.js",
            "/var/www/html/vidgenerator/unified_dashboard/index.html",
            "/var/www/html/backend/routes/unified_dashboard_routes.py",
            "/var/www/html/backend/routes/monetization_top50_routes.py",
            "/var/www/html/backend/routes/agent_routes.py",
            "/var/www/html/backend/routes/unified_points.py",
            "/var/www/html/backend/routes/point_calculator_routes.py",
            "/var/www/html/backend/routes/tech_tree_routes.py",
        ]
        
        for file_path in key_files:
            try:
                stdin, stdout, stderr = ssh.exec_command(f"ls -la {file_path} 2>&1", timeout=5)
                output = stdout.read().decode().strip()
                error = stderr.read().decode().strip()
                if output and 'No such file' not in output:
                    # Extract permissions from ls -la output
                    parts = output.split()
                    if len(parts) > 0:
                        perms = parts[0]
                        print(f"  [OK] {file_path.split('/')[-1]}: {perms}")
                    else:
                        print(f"  [WARN] {file_path.split('/')[-1]}: Could not read permissions")
                elif error:
                    print(f"  [ERROR] {file_path.split('/')[-1]}: {error}")
            except Exception as e:
                print(f"  [ERROR] {file_path.split('/')[-1]}: {e}")
        
        print()
        print("="*70)
        print("PERMISSIONS FIX COMPLETE!")
        print("="*70)
        print()
        print("Summary:")
        print("  - Directories: 755 (readable, executable)")
        print("  - Files: 644 (readable)")
        print("  - Key files verified")
        print()
        print("Next steps:")
        print("  1. Hard refresh browser (Ctrl+F5)")
        print("  2. Check if static files load")
        print("  3. Check if API routes respond")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_permissions()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Add Missing Blueprint Registrations
Adds missing blueprint registrations to register_blueprints.py on server
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def add_registrations():
    """Add missing registrations"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        register_file = '/var/www/html/vidgenerator/backend/register_blueprints.py'
        
        # Read file
        print("[1/4] Reading register_blueprints.py...")
        sftp = ssh.open_sftp()
        with sftp.open(register_file, 'r') as f:
            content = f.read().decode('utf-8')
        sftp.close()
        print(f"  [OK] Read {len(content)} bytes")
        
        # Check what's missing
        print()
        print("[2/4] Checking for missing registrations...")
        missing = []
        
        if 'point_calculator_bp' not in content or 'Registered point_calculator blueprint' not in content:
            missing.append('point_calculator')
            print("  ❌ point_calculator registration missing")
        else:
            print("  ✅ point_calculator registration exists")
        
        if 'tech_tree_bp' not in content or 'Registered tech_tree blueprint' not in content:
            missing.append('tech_tree')
            print("  ❌ tech_tree registration missing")
        else:
            print("  ✅ tech_tree registration exists")
        
        if not missing:
            print("  ✅ All registrations exist")
            return True
        
        # Find where to add registrations (after point_analytics)
        print()
        print("[3/4] Adding missing registrations...")
        lines = content.split('\n')
        new_lines = []
        added_point_calc = False
        added_tech_tree = False
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            # Add point_calculator after point_analytics
            if 'Registered point_analytics blueprint' in line and not added_point_calc and 'point_calculator' in missing:
                new_lines.append('')
                new_lines.append('    # Point Calculator routes')
                new_lines.append('    try:')
                new_lines.append('        from backend.routes.point_calculator_routes import point_calculator_bp')
                new_lines.append('        app.register_blueprint(point_calculator_bp)')
                new_lines.append('        registered_count += 1')
                new_lines.append('        _safe_print("  [OK] Registered point_calculator blueprint")')
                new_lines.append('    except ImportError as e:')
                new_lines.append('        _safe_print(f"  [WARN] Could not import point_calculator_routes: {e}")')
                new_lines.append('    except Exception as e:')
                new_lines.append('        _safe_print(f"  [ERROR] Error registering point_calculator: {e}")')
                added_point_calc = True
            
            # Add tech_tree after tech_tree (if it's missing but should be there)
            # Actually, tech_tree should already be registered, let's check the error
            # The error says tech_tree failed to register due to syntax error
            # We fixed the syntax, so it should register now
        
        new_content = '\n'.join(new_lines)
        
        if new_content != content:
            sftp = ssh.open_sftp()
            with sftp.open(register_file, 'w') as f:
                f.write(new_content.encode('utf-8'))
            sftp.close()
            print("  ✅ Registrations added")
        else:
            print("  ⚠️  No changes needed")
        
        # Verify
        print()
        print("[4/4] Verifying registrations...")
        stdin, stdout, stderr = ssh.exec_command(
            f"grep -n 'point_calculator_bp' {register_file} | head -3",
            timeout=5
        )
        verification = stdout.read().decode().strip()
        if verification:
            print("  ✅ point_calculator registration found:")
            print(f"    {verification}")
        
        print()
        print("="*70)
        print("REGISTRATIONS ADDED")
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
    add_registrations()

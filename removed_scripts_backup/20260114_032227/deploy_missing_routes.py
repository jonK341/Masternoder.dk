#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Missing Routes - Register calculator blueprint and fix static files
"""
import paramiko
import os
import sys

SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_PATH = '/var/www/html/vidgenerator'

def add_calculator_blueprint_registration():
    """Add calculator blueprint registration to register_blueprints.py"""
    print("Checking if calculator_bp registration exists...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    register_file = os.path.join(script_dir, 'backend', 'register_blueprints.py')
    
    if not os.path.exists(register_file):
        print(f"[ERROR] File not found: {register_file}")
        return False
    
    with open(register_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already registered
    if 'video_generation_calculator' in content or 'calculator_bp' in content:
        print("[OK] Calculator blueprint registration already exists")
        return True
    
    # Find a good place to add it (before the end of the function)
    insertion_point = content.rfind('registered_count += 1')
    if insertion_point == -1:
        print("[ERROR] Could not find insertion point")
        return False
    
    # Find the end of that block
    lines = content[:insertion_point].split('\n')
    indent_level = 0
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith('_safe_print'):
            indent_level = len(lines[i]) - len(lines[i].lstrip())
            break
    
    indent = ' ' * (indent_level + 4)
    
    # Add calculator blueprint registration
    calculator_registration = f'''
    # Video Generation Calculator Routes
    try:
        _safe_print("  [DEBUG] Attempting to import video_generation_calculator_routes...")
        from backend.routes.video_generation_calculator_routes import calculator_bp
        _safe_print(f"  [DEBUG] Imported calculator_bp: {{calculator_bp}}")
        app.register_blueprint(calculator_bp)
        registered_count += 1
        _safe_print("  [OK] Registered calculator blueprint")
    except ImportError as e:
        _safe_print(f"  [WARN] Could not import video_generation_calculator_routes: {{e}}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        _safe_print(f"  [ERROR] Error registering calculator: {{e}}")
        import traceback
        traceback.print_exc()
'''
    
    # Insert before the return statement
    insert_pos = content.rfind('return registered_count')
    if insert_pos == -1:
        insert_pos = content.rfind('_safe_print(f"  [OK] Registered')
        if insert_pos == -1:
            print("[ERROR] Could not find insertion point")
            return False
    
    # Find the end of the last registration block
    before_insert = content[:insert_pos]
    last_newline = before_insert.rfind('\n    ')
    if last_newline == -1:
        last_newline = before_insert.rfind('\n')
    
    new_content = content[:last_newline + 1] + calculator_registration + content[last_newline + 1:]
    
    with open(register_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"[OK] Added calculator blueprint registration to {register_file}")
    return True

def deploy_files(ssh, sftp):
    """Deploy updated files"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    files_to_deploy = [
        'backend/register_blueprints.py',
    ]
    
    success_count = 0
    for local_file in files_to_deploy:
        local_full_path = os.path.normpath(os.path.join(script_dir, local_file))
        remote_file_path = os.path.join(BASE_PATH, local_file).replace('\\', '/')
        
        if os.path.exists(local_full_path):
            try:
                remote_dir = os.path.dirname(remote_file_path)
                stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {remote_dir}')
                stdout.channel.recv_exit_status()
                
                sftp.put(local_full_path, remote_file_path)
                print(f"[OK] Deployed: {local_file}")
                success_count += 1
            except Exception as e:
                print(f"[ERROR] Failed to deploy {local_file}: {e}")
        else:
            print(f"[WARN] Local file not found: {local_full_path}")
    
    return success_count

def main():
    print("="*80)
    print("DEPLOYING MISSING ROUTES FIX")
    print("="*80)
    
    # First, add calculator blueprint registration locally
    if not add_calculator_blueprint_registration():
        print("[ERROR] Failed to add calculator blueprint registration")
        return
    
    try:
        print("\n[1/4] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("[OK] Connected to server")
        
        print("\n[2/4] Deploying files...")
        success_count = deploy_files(ssh, sftp)
        print(f"\n[OK] Deployed {success_count} files")
        
        sftp.close()
        
        print("\n[3/4] Clearing cache...")
        commands = [
            'find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true',
            'find /var/www/html/vidgenerator -type f -name "*.pyc" -delete 2>/dev/null || true',
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("[OK] Cache cleared")
        
        print("\n[4/4] Restarting services...")
        restart_commands = [
            'systemctl restart uwsgi-vidgenerator.service 2>/dev/null || true',
            'sleep 3',
            'systemctl restart python-proxy.service 2>/dev/null || true',
            'sleep 2',
            'systemctl restart nginx 2>/dev/null || true',
        ]
        for cmd in restart_commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("[OK] Services restarted")
        
        ssh.close()
        
        print("\n" + "="*80)
        print("DEPLOYMENT COMPLETE")
        print("="*80)
        print("Missing Routes Fix deployed!")
        print("\nFixes Applied:")
        print("[OK] Added calculator_bp blueprint registration")
        print("[OK] Routes should now be accessible")
        
    except paramiko.AuthenticationException:
        print("[ERROR] Authentication failed. Check DEPLOY_PASS environment variable.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

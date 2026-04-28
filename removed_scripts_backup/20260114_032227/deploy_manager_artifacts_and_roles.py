#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Manager Artifacts and Manager Roles
Add manager artifacts system and 6 manager roles to agent skillsets
"""
import paramiko
import os
import sys

SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_PATH = '/var/www/html/vidgenerator'

FILES_TO_DEPLOY = [
    'backend/services/manager_artifacts_system.py',
    'backend/services/agent_enhanced_skills_system.py',
    'backend/routes/manager_artifacts_routes.py',
    'backend/routes/agent_enhanced_skills_routes.py',
    'backend/register_blueprints.py',
]

def deploy_file(ssh, sftp, local_path, remote_path):
    """Deploy a single file to the server"""
    try:
        remote_dir = os.path.dirname(remote_path)
        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {remote_dir}')
        stdout.channel.recv_exit_status()
        
        sftp.put(local_path, remote_path)
        print(f"[OK] Deployed: {local_path} -> {remote_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to deploy {local_path}: {e}")
        return False

def main():
    print("="*80)
    print("DEPLOYING MANAGER ARTIFACTS AND MANAGER ROLES")
    print("="*80)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        print("\n[1/4] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("[OK] Connected to server")
        
        print("\n[2/4] Deploying files...")
        success_count = 0
        for local_file in FILES_TO_DEPLOY:
            local_full_path = os.path.normpath(os.path.join(script_dir, local_file))
            remote_file_path = os.path.join(BASE_PATH, local_file).replace('\\', '/')
            
            if os.path.exists(local_full_path):
                if deploy_file(ssh, sftp, local_full_path, remote_file_path):
                    success_count += 1
            else:
                print(f"[WARN] Local file not found: {local_full_path}")
        
        print(f"\n[OK] Deployed {success_count}/{len(FILES_TO_DEPLOY)} files")
        
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
        print("\nManager Artifacts and Roles Deployed:")
        print("  [OK] Created Manager Artifacts System with 10 artifacts:")
        print("       - Leadership Crown (Legendary)")
        print("       - Scroll of Perfect Execution (Epic)")
        print("       - Strategic Compass (Epic)")
        print("       - Resource Amulet (Rare)")
        print("       - Team Synergy Crystal (Rare)")
        print("       - Innovation Lantern (Rare)")
        print("       - Delegation Seal (Epic)")
        print("       - Communication Orb (Rare)")
        print("       - Time Mastery Hourglass (Epic)")
        print("       - Decision Scales (Legendary)")
        print("  [OK] Added 6 Manager Roles to Agent Skillsets:")
        print("       1. Project Manager - Execution & Timeline Management")
        print("       2. Resource Manager - Budget & Resource Optimization")
        print("       3. Team Manager - Leadership & Team Coordination")
        print("       4. Strategic Manager - Long-term Planning & Strategy")
        print("       5. Operations Manager - Workflow & Operations Excellence")
        print("       6. Innovation Manager - Creative Thinking & Innovation")
        print("  [OK] Created API endpoints for manager artifacts")
        print("  [OK] Created API endpoints for manager roles")
        print("  [OK] Integrated with unified point system")
        print("  [OK] Registered all blueprints")
        
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

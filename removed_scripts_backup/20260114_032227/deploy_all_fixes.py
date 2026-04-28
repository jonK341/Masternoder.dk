#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy all fixes for unified dashboard, tech tree, and API endpoints
"""
import paramiko
import os
import sys

# Server configuration
SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_PATH = '/var/www/html/vidgenerator'

# Files to deploy
FILES_TO_DEPLOY = [
    'backend/routes/comprehensive_fixes_routes.py',
    'backend/routes/unified_dashboard_routes.py',
    'backend/routes/victory_tech_tree.py',
    'backend/routes/all_page_routes.py',
    'backend/routes/battle.py',
    'backend/routes/game.py',
    'backend/routes/generator.py',
    'backend/routes/ai_video_clip_routes.py',
    'backend/routes/system_fix_routes.py',
    'backend/routes/frontpage_init_routes.py',
    'backend/routes/comprehensive_skills_abilities_routes.py',
    'backend/routes/intelligent_points_routes.py',
    'backend/routes/battle_stats_endpoints.py',
    'backend/routes/battle_intelligence_routes.py',
    'backend/routes/battle_tech_tree_routes.py',
    'backend/services/game_agent.py',
    'backend/routes/game_agent_routes.py',
    'backend/register_blueprints.py',
]

def deploy_file(ssh, sftp, local_path, remote_path):
    """Deploy a single file"""
    try:
        # Ensure remote directory exists
        remote_dir = os.path.dirname(remote_path)
        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {remote_dir}')
        stdout.channel.recv_exit_status()  # Wait for command to complete
        
        # Deploy file
        sftp.put(local_path, remote_path)
        print(f"[OK] Deployed: {local_path} -> {remote_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to deploy {local_path}: {e}")
        return False

def main():
    print("="*80)
    print("DEPLOYING ALL FIXES")
    print("="*80)
    
    try:
        # Connect to server
        print("\n[1/4] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("[OK] Connected to server")
        
        # Deploy files
        print("\n[2/4] Deploying files...")
        deployed_count = 0
        script_dir = os.path.dirname(os.path.abspath(__file__))
        for local_file in FILES_TO_DEPLOY:
            # Normalize path separators for Windows
            local_path = os.path.normpath(os.path.join(script_dir, local_file))
            remote_file = os.path.join(BASE_PATH, local_file).replace('\\', '/')
            if os.path.exists(local_path):
                if deploy_file(ssh, sftp, local_path, remote_file):
                    deployed_count += 1
            else:
                print(f"[WARN] File not found locally: {local_path}")
        
        sftp.close()
        print(f"\n[OK] Deployed {deployed_count}/{len(FILES_TO_DEPLOY)} files")
        
        # Clear Python cache
        print("\n[3/4] Clearing Python cache...")
        commands = [
            'find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true',
            'find /var/www/html/vidgenerator -type f -name "*.pyc" -delete 2>/dev/null || true',
        ]
        for cmd in commands:
            ssh.exec_command(cmd)
        print("[OK] Cache cleared")
        
        # Restart services
        print("\n[4/4] Restarting services...")
        # NOTE: Production uses uwsgi-vidgenerator.service (not only the legacy `uwsgi` init script)
        restart_cmd = (
            'systemctl restart uwsgi-vidgenerator.service 2>/dev/null || true; '
            'systemctl restart uwsgi 2>/dev/null || true; '
            'systemctl restart python-proxy.service 2>/dev/null || true; '
            'systemctl restart nginx 2>/dev/null || true'
        )
        stdin, stdout, stderr = ssh.exec_command(restart_cmd)
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("[OK] Services restarted successfully")
        else:
            error_output = stderr.read().decode('utf-8', errors='ignore')
            print(f"[WARN] Service restart completed with warnings: {error_output[:200]}")
        
        ssh.close()
        
        print("\n" + "="*80)
        print("DEPLOYMENT COMPLETE")
        print("="*80)
        print(f"Deployed: {deployed_count} files")
        print("Services: Restarted")
        print("\nPlease wait 10-15 seconds for services to fully restart,")
        print("then run the comprehensive_site_audit.py to verify fixes.")
        
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

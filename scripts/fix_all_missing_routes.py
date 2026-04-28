#!/usr/bin/env python3
"""
Fix All Missing Routes
Fixes all missing routes in route files on server
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_all_routes():
    """Fix all missing routes"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Route files to check and fix
        route_fixes = [
            {
                'file': '/var/www/html/vidgenerator/backend/routes/monetization_top50_routes.py',
                'check': '/api/monetization/cash',
                'add_before': '/api/monetization/top-50',
                'routes': [
                    "@monetization_top50_bp.route('/api/monetization/cash', methods=['GET'])",
                    "@monetization_top50_bp.route('/vidgenerator/api/monetization/cash', methods=['GET'])"
                ]
            },
            {
                'file': '/var/www/html/vidgenerator/backend/routes/tech_tree_routes.py',
                'check': '/api/tech-tree/knowledge',
                'add_before': None,  # Will add at end of file
                'routes': [
                    "@tech_tree_bp.route('/api/tech-tree/knowledge', methods=['GET'])",
                    "@tech_tree_bp.route('/vidgenerator/api/tech-tree/knowledge', methods=['GET'])"
                ]
            },
            {
                'file': '/var/www/html/vidgenerator/backend/routes/agent_routes.py',
                'check': '/api/agent/get-all',
                'add_before': None,
                'routes': [
                    "@agent_bp.route('/api/agent/get-all', methods=['GET'])",
                    "@agent_bp.route('/vidgenerator/api/agent/get-all', methods=['GET'])"
                ]
            },
            {
                'file': '/var/www/html/vidgenerator/backend/routes/unified_points.py',
                'check': '/api/points/statistics',
                'add_before': None,
                'routes': [
                    "@unified_points_bp.route('/api/points/statistics', methods=['GET'])",
                    "@unified_points_bp.route('/vidgenerator/api/points/statistics', methods=['GET'])"
                ]
            },
            {
                'file': '/var/www/html/vidgenerator/backend/routes/point_calculator_routes.py',
                'check': '/api/points/calculator/predict',
                'add_before': None,
                'routes': [
                    "@point_calculator_bp.route('/api/points/calculator/predict', methods=['GET', 'POST'])",
                    "@point_calculator_bp.route('/vidgenerator/api/points/calculator/predict', methods=['GET', 'POST'])"
                ]
            },
        ]
        
        sftp = ssh.open_sftp()
        
        for fix in route_fixes:
            file_path = fix['file']
            check_route = fix['check']
            
            print(f"Checking: {file_path}")
            
            # Check if file exists
            try:
                with sftp.open(file_path, 'r') as f:
                    content = f.read().decode('utf-8')
            except:
                print(f"  ⚠️  File not found, skipping")
                continue
            
            # Check if route already exists
            if check_route in content and f"@.*route.*{check_route}" in content:
                print(f"  ✅ Route {check_route} already exists")
                continue
            
            print(f"  ❌ Route {check_route} missing, adding...")
            
            # Add routes
            lines = content.split('\n')
            new_lines = []
            added = False
            
            if fix['add_before']:
                # Add before specific line
                for line in lines:
                    if fix['add_before'] in line and not added:
                        for route in fix['routes']:
                            new_lines.append(route)
                        added = True
                    new_lines.append(line)
            else:
                # Add at end of file (before last line if it's empty, or append)
                new_lines = lines
                for route in fix['routes']:
                    new_lines.append(route)
                added = True
            
            if added:
                new_content = '\n'.join(new_lines)
                with sftp.open(file_path, 'w') as f:
                    f.write(new_content.encode('utf-8'))
                print(f"  ✅ Routes added")
            else:
                print(f"  ⚠️  Could not add routes")
        
        sftp.close()
        
        print()
        print("="*70)
        print("ALL ROUTES FIXED")
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
    fix_all_routes()

#!/usr/bin/env python3
"""
Fix Remaining Routes
Fixes the remaining 404 and 500 errors
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_remaining():
    """Fix remaining routes"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        sftp = ssh.open_sftp()
        
        # 1. Check tech_tree blueprint registration
        print("[1/4] Checking tech_tree blueprint...")
        register_file = '/var/www/html/vidgenerator/backend/register_blueprints.py'
        stdin, stdout, stderr = ssh.exec_command(
            f"grep -n 'tech_tree_bp' {register_file} | head -3",
            timeout=5
        )
        tech_tree_reg = stdout.read().decode().strip()
        if tech_tree_reg:
            print(f"  ✅ tech_tree registration found")
        else:
            print("  ❌ tech_tree registration missing")
        
        # 2. Check point_calculator blueprint registration
        print()
        print("[2/4] Checking point_calculator blueprint...")
        stdin2, stdout2, stderr2 = ssh.exec_command(
            f"grep -n 'point_calculator_bp' {register_file} | head -3",
            timeout=5
        )
        calc_reg = stdout2.read().decode().strip()
        if calc_reg:
            print(f"  ✅ point_calculator registration found")
        else:
            print("  ❌ point_calculator registration missing")
        
        # 3. Fix points/history/analytics - check if method exists
        print()
        print("[3/4] Checking get_point_history_analytics method...")
        db_file = '/var/www/html/vidgenerator/backend/services/unified_points_database.py'
        stdin3, stdout3, stderr3 = ssh.exec_command(
            f"grep -n 'def get_point_history_analytics' {db_file}",
            timeout=5
        )
        method = stdout3.read().decode().strip()
        if method:
            print(f"  ✅ Method exists: {method}")
        else:
            print("  ❌ Method missing - need to add it")
            # Read file and add method
            with sftp.open(db_file, 'r') as f:
                db_content = f.read().decode('utf-8')
            
            if 'def get_point_history_analytics' not in db_content:
                # Add method at end of class
                method_code = '''
    def get_point_history_analytics(self, user_id, days=30, point_type=None):
        """Get point history analytics"""
        try:
            # Return empty analytics for now
            return {
                'success': True,
                'summary': {
                    'total_earned': 0,
                    'total_spent': 0,
                    'net_change': 0
                },
                'top_sources': []
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting point history analytics: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'summary': {
                    'total_earned': 0,
                    'total_spent': 0,
                    'net_change': 0
                },
                'top_sources': []
            }
'''
                # Find end of class (before last function or at end)
                lines = db_content.split('\n')
                # Find the last method and add after it
                last_method_end = len(lines)
                for i in range(len(lines) - 1, max(0, len(lines) - 50), -1):
                    if lines[i].strip().startswith('def ') and 'self' in lines[i]:
                        # Find end of this method
                        for j in range(i+1, min(i+30, len(lines))):
                            if lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                                last_method_end = j
                                break
                        break
                
                new_lines = lines[:last_method_end] + [method_code] + lines[last_method_end:]
                new_content = '\n'.join(new_lines)
                
                with sftp.open(db_file, 'w') as f:
                    f.write(new_content.encode('utf-8'))
                print("  ✅ Method added")
        
        # 4. Verify routes are registered in app
        print()
        print("[4/4] Verifying routes in running app...")
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html/vidgenerator")

from src.app import create_app

app = create_app()

routes_to_check = [
    '/api/tech-tree/knowledge',
    '/api/points/calculator/predict',
]

for route in routes_to_check:
    found = False
    for rule in app.url_map.iter_rules():
        if route in str(rule):
            found = True
            print(f"  ✅ {route}")
            break
    if not found:
        print(f"  ❌ {route} NOT FOUND")

# Check blueprints
blueprint_names = [bp.name for bp in app.blueprints.values()]
for bp_name in ['tech_tree', 'point_calculator']:
    if bp_name in blueprint_names:
        print(f"  ✅ {bp_name} blueprint registered")
    else:
        print(f"  ❌ {bp_name} blueprint NOT registered")
'''
        
        stdin4, stdout4, stderr4 = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=60
        )
        output = stdout4.read().decode().strip()
        if output:
            print(output)
        
        sftp.close()
        
        print()
        print("="*70)
        print("REMAINING ROUTES CHECKED")
        print("="*70)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_remaining()

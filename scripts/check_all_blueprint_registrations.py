#!/usr/bin/env python3
"""
Check All Blueprint Registrations
Lists all registered blueprints and their routes
"""
import paramiko
import os
import json

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_blueprints():
    """Check all blueprint registrations"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html/vidgenerator")
from src.app import create_app

app = create_app()

# Get all blueprints
blueprints = {}
for name, bp in app.blueprints.items():
    blueprints[name] = {
        'name': name,
        'import_name': bp.import_name if hasattr(bp, 'import_name') else None,
        'url_prefix': bp.url_prefix if hasattr(bp, 'url_prefix') else None
    }

# Get all routes grouped by blueprint
routes_by_blueprint = {}
for rule in app.url_map.iter_rules():
    if rule.endpoint != 'static':
        blueprint_name = rule.endpoint.split('.')[0] if '.' in rule.endpoint else 'app'
        if blueprint_name not in routes_by_blueprint:
            routes_by_blueprint[blueprint_name] = []
        routes_by_blueprint[blueprint_name].append({
            'rule': str(rule),
            'methods': list(rule.methods),
            'endpoint': rule.endpoint
        })

import json
print(json.dumps({
    'blueprints': blueprints,
    'routes_by_blueprint': routes_by_blueprint,
    'total_blueprints': len(blueprints),
    'total_routes': sum(len(routes) for routes in routes_by_blueprint.values())
}))
'''
        
        print("[1/1] Getting blueprint registrations...")
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=120
        )
        output = stdout.read().decode('utf-8', errors='ignore').strip()
        error = stderr.read().decode('utf-8', errors='ignore').strip()
        
        # Filter out startup logs
        lines = output.split('\n')
        json_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith('{'):
                json_start = i
                break
        
        if json_start is not None:
            json_output = '\n'.join(lines[json_start:])
            try:
                data = json.loads(json_output)
                
                print()
                print("="*80)
                print("BLUEPRINT REGISTRATION REPORT")
                print("="*80)
                print()
                print(f"Total Blueprints: {data.get('total_blueprints', 0)}")
                print(f"Total Routes: {data.get('total_routes', 0)}")
                print()
                
                # Show critical blueprints
                critical_blueprints = [
                    'unified_dashboard', 'monetization', 'agent', 'unified_points',
                    'point_analytics', 'point_calculator', 'tech_tree', 'leaderboard_unified'
                ]
                
                print("CRITICAL BLUEPRINTS:")
                for bp_name in critical_blueprints:
                    if bp_name in data.get('blueprints', {}):
                        bp = data['blueprints'][bp_name]
                        route_count = len(data.get('routes_by_blueprint', {}).get(bp_name, []))
                        print(f"  ✅ {bp_name}: {route_count} routes")
                    else:
                        print(f"  ❌ {bp_name}: NOT REGISTERED")
                print()
                
                # Show routes for critical blueprints
                print("ROUTES BY BLUEPRINT:")
                for bp_name in critical_blueprints:
                    routes = data.get('routes_by_blueprint', {}).get(bp_name, [])
                    if routes:
                        print(f"\n  {bp_name} ({len(routes)} routes):")
                        for route in routes[:10]:  # Show first 10
                            print(f"    - {route['rule']} [{', '.join(route['methods'])}]")
                        if len(routes) > 10:
                            print(f"    ... and {len(routes) - 10} more")
                
                ssh.close()
                return data
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                print("Raw output:")
                print(output[-2000:])  # Last 2000 chars
        
        ssh.close()
        return None
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    check_blueprints()

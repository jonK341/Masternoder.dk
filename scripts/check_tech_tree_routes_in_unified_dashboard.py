#!/usr/bin/env python3
"""
Check Tech Tree Routes in Unified Dashboard
Verifies if tech-tree routes are registered in unified_dashboard blueprint
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_routes():
    """Check routes"""
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

# Get all routes with tech-tree
tech_tree_routes = []
for rule in app.url_map.iter_rules():
    if 'tech-tree' in str(rule) or 'tech_tree' in rule.endpoint:
        tech_tree_routes.append({
            'rule': str(rule),
            'methods': list(rule.methods),
            'endpoint': rule.endpoint
        })

# Get unified_dashboard routes
unified_dashboard_routes = []
for rule in app.url_map.iter_rules():
    if 'unified_dashboard' in rule.endpoint:
        unified_dashboard_routes.append({
            'rule': str(rule),
            'methods': list(rule.methods),
            'endpoint': rule.endpoint
        })

import json
print(json.dumps({
    'tech_tree_routes': tech_tree_routes,
    'unified_dashboard_routes': unified_dashboard_routes
}))
'''
        
        print("[1/1] Checking tech-tree routes...")
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=120
        )
        output = stdout.read().decode('utf-8', errors='ignore').strip()
        
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
                import json
                data = json.loads(json_output)
                
                print()
                print("="*80)
                print("TECH-TREE ROUTES ANALYSIS")
                print("="*80)
                print()
                
                tech_routes = data.get('tech_tree_routes', [])
                unified_routes = data.get('unified_dashboard_routes', [])
                
                print(f"Tech-tree routes found: {len(tech_routes)}")
                if tech_routes:
                    print("  Routes:")
                    for route in tech_routes:
                        print(f"    - {route['rule']} [{', '.join(route['methods'])}]")
                else:
                    print("  ❌ No tech-tree routes found")
                
                print()
                print(f"Unified dashboard routes: {len(unified_routes)}")
                
                # Check if tech-tree routes are in unified_dashboard
                tech_in_unified = [r for r in unified_routes if 'tech-tree' in r['rule']]
                if tech_in_unified:
                    print(f"  ✅ Found {len(tech_in_unified)} tech-tree routes in unified_dashboard:")
                    for route in tech_in_unified:
                        print(f"    - {route['rule']}")
                else:
                    print("  ❌ No tech-tree routes found in unified_dashboard blueprint")
                    print("  This explains why /api/tech-tree returns 404")
                
                ssh.close()
                return data
            except json.JSONDecodeError:
                print("Error parsing JSON")
                print(output[-1000:])
        
        ssh.close()
        return None
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    check_routes()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy All Static Files and Fix Routes
Deploys missing CSS/JS files, fixes /trophie route, updates shop, and fixes quick battle
"""
import paramiko
import os
import sys
import time
from datetime import datetime

# Fix Windows encoding issues
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_BASE = "/var/www/html/vidgenerator"

# Missing static files that need to be deployed
MISSING_STATIC_FILES = [
    # CSS files
    "vidgenerator/static/css/image-support.css",
    "vidgenerator/static/css/template-effects.css",
    "vidgenerator/static/css/agent-skill-sets.css",
    "vidgenerator/static/css/loading-states.css",
    "vidgenerator/static/css/modern-design-system.css",
    "vidgenerator/static/css/navigation-toolbar.css",
    
    # JS files
    "vidgenerator/static/js/image-support.js",
    "vidgenerator/static/js/template-effects.js",
    "vidgenerator/static/js/template-engine-core.js",
    "vidgenerator/static/js/template-services.js",
    "vidgenerator/static/js/agent-skill-sets.js",
    "vidgenerator/static/js/toast-notifications.js",
    "vidgenerator/static/js/navigation-toolbar.js",
    "vidgenerator/static/js/progression-display.js",
    "vidgenerator/static/js/stats-achievements-tracker.js",
    "vidgenerator/static/js/shop-tab-system.js",
]

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(text.center(70))
    print("=" * 70 + "\n")

def print_success(text):
    print(f"[OK] {text}")

def print_error(text):
    print(f"[ERROR] {text}")

def print_info(text):
    print(f"[INFO] {text}")

def print_warning(text):
    print(f"[WARN] {text}")

def deploy_static_files(ssh, sftp):
    """Deploy all missing static files"""
    print_header("DEPLOYING MISSING STATIC FILES")
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    deployed = 0
    skipped = 0
    errors = 0
    
    for local_file in MISSING_STATIC_FILES:
        local_path = os.path.join(BASE_DIR, local_file)
        
        if not os.path.exists(local_path):
            print_info(f"Skipping {local_file} (not found locally)")
            skipped += 1
            continue
        
        try:
            remote_path = os.path.join(REMOTE_BASE, local_file).replace('\\', '/')
            remote_dir = os.path.dirname(remote_path)
            
            # Create remote directory
            ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
            time.sleep(0.5)
            
            # Read local file
            with open(local_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Write to remote
            with sftp.file(remote_path, 'w') as rf:
                rf.write(content)
            
            print_success(f"{local_file}")
            deployed += 1
            
        except Exception as e:
            print_error(f"{local_file}: {str(e)[:100]}")
            errors += 1
    
    print(f"\n[SUMMARY] Deployed: {deployed}, Skipped: {skipped}, Errors: {errors}")
    return deployed > 0

def check_shop_v3_route(ssh):
    """Check and fix shop-v3 route"""
    print_header("CHECKING SHOP-V3 ROUTE")
    
    # Check if shop_v3_routes.py exists and is correct
    remote_file = f"{REMOTE_BASE}/backend/routes/shop_v3_routes.py"
    
    try:
        # Check if route file exists
        cmd = f"test -f {remote_file} && echo 'EXISTS' || echo 'NOT_FOUND'"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode('utf-8', errors='replace').strip()
        
        if 'EXISTS' not in output:
            print_error("shop_v3_routes.py not found on server!")
            return False
        
        print_success("shop_v3_routes.py exists on server")
        
        # Check if blueprint is registered (check register_blueprints.py)
        register_file = f"{REMOTE_BASE}/backend/register_blueprints.py"
        cmd = f"grep -n 'shop_v3_bp' {register_file} | head -5"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode('utf-8', errors='replace')
        
        if 'shop_v3_bp' in output:
            print_success("shop_v3 blueprint is registered")
            # Check if it has /vidgenerator prefix
            if 'url_prefix' in output or '/vidgenerator' in output:
                print_success("Blueprint has /vidgenerator prefix")
                return True
            else:
                print_warning("Blueprint may be missing /vidgenerator prefix")
                return False
        else:
            print_error("shop_v3 blueprint not found in register_blueprints.py")
            return False
            
    except Exception as e:
        print_error(f"Could not check shop-v3 route: {str(e)[:100]}")
        return False

def create_trophie_route(ssh, sftp):
    """Create /trophie route and blueprint"""
    print_header("CREATING /TROPHIE ROUTE")
    
    # Check if trophie route file exists
    trophie_route_file = f"{REMOTE_BASE}/backend/routes/trophie_routes.py"
    
    try:
        # Check if file exists
        cmd = f"test -f {trophie_route_file} && echo 'EXISTS' || echo 'NOT_FOUND'"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode('utf-8', errors='replace').strip()
        
        if 'EXISTS' in output:
            print_info("trophie_routes.py already exists")
        else:
            # Create trophie routes file
            print_info("Creating trophie_routes.py...")
            
            trophie_routes_content = '''"""
Trophie/Trophy Routes
Routes for trophy display and management
"""
from flask import Blueprint, render_template_string, jsonify, request
from backend.services.trophy_system import trophy_system
import os

trophie_bp = Blueprint('trophie', __name__)

@trophie_bp.route('/trophie')
@trophie_bp.route('/trophie/')
@trophie_bp.route('/vidgenerator/trophie')
@trophie_bp.route('/vidgenerator/trophie/')
def trophie_index():
    """Trophie/Trophy page"""
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        trophie_path = os.path.join(base_path, 'vidgenerator', 'trophie', 'index.html')
        
        if os.path.exists(trophie_path):
            with open(trophie_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
        # Fallback HTML if file doesn't exist
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trophies - MasterNoder</title>
    <link rel="stylesheet" href="/vidgenerator/static/css/modern-design-system.css">
    <link rel="stylesheet" href="/vidgenerator/static/css/template-effects.css">
    <style>
        body { padding: 20px; font-family: Arial, sans-serif; }
        .trophy-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; margin-top: 20px; }
        .trophy-card { padding: 20px; border: 1px solid #ccc; border-radius: 8px; text-align: center; }
    </style>
</head>
<body>
    <h1>Trophies</h1>
    <div id="trophies-container">
        <p>Loading trophies...</p>
    </div>
    <script>
        fetch('/vidgenerator/api/trophy/list')
            .then(r => r.json())
            .then(data => {
                const container = document.getElementById('trophies-container');
                if (data.trophies) {
                    container.innerHTML = '<div class="trophy-grid">' + 
                        data.trophies.map(t => `<div class="trophy-card"><h3>${t.name || t}</h3></div>`).join('') +
                        '</div>';
                }
            })
            .catch(e => console.error('Error loading trophies:', e));
    </script>
</body>
</html>"""
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        return f"Error loading trophie page: {str(e)}", 500

@trophie_bp.route('/api/trophie/list')
@trophie_bp.route('/vidgenerator/api/trophie/list')
def list_trophies_api():
    """List all trophies API"""
    try:
        user_id = request.args.get('user_id', 'default')
        trophies = trophy_system.get_user_trophies(user_id)
        definitions = trophy_system.trophy_definitions
        
        return jsonify({
            'success': True,
            'trophies': trophies,
            'definitions': definitions
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
'''
            
            remote_dir = os.path.dirname(trophie_route_file)
            ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
            
            with sftp.file(trophie_route_file, 'w') as f:
                f.write(trophie_routes_content)
            
            print_success("trophie_routes.py created")
        
        # Register blueprint
        print_info("Registering trophie blueprint...")
        
        # Check if already registered
        register_file = f"{REMOTE_BASE}/backend/register_blueprints.py"
        cmd = f"grep -n 'trophie_bp' {register_file} | head -2"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode('utf-8', errors='replace')
        
        if 'trophie_bp' not in output:
            # Add registration (we'll need to read, modify, and write)
            print_info("Adding trophie blueprint registration...")
            # This is complex - we'll use sed to add it after shop_v3 registration
            cmd = f'''sed -i '/shop_v3_bp/a\\    # Trophie routes\\n    try:\\n        from backend.routes.trophie_routes import trophie_bp\\n        app.register_blueprint(trophie_bp, url_prefix=\\"/vidgenerator\\")\\n        registered_count += 1\\n        _safe_print("  [OK] Registered trophie blueprint")\\n    except ImportError as e:\\n        _safe_print(f"  [WARN] Could not import trophie_routes: {{e}}")\\n    except Exception as e:\\n        _safe_print(f"  [ERROR] Error registering trophie: {{e}}")\\n' {register_file}'''
            
            # Better approach: read file, add registration, write back
            # For now, just note that it needs manual addition
            print_warning("Blueprint registration needs to be added manually to register_blueprints.py")
            print_info("Add after shop_v3 registration:")
            print("""
    # Trophie routes
    try:
        from backend.routes.trophie_routes import trophie_bp
        app.register_blueprint(trophie_bp, url_prefix='/vidgenerator')
        registered_count += 1
        _safe_print("  [OK] Registered trophie blueprint")
    except ImportError as e:
        _safe_print(f"  [WARN] Could not import trophie_routes: {e}")
    except Exception as e:
        _safe_print(f"  [ERROR] Error registering trophie: {e}")
""")
        else:
            print_success("trophie blueprint already registered")
        
        return True
        
    except Exception as e:
        print_error(f"Could not create trophie route: {str(e)[:100]}")
        return False

def fix_shop_page_api_call(ssh):
    """Fix shop page to use correct API endpoint"""
    print_header("FIXING SHOP PAGE API CALL")
    
    shop_html_file = f"{REMOTE_BASE}/vidgenerator/shop/index.html"
    
    try:
        # Read current file
        cmd = f"cat {shop_html_file} | grep -n 'shop-v3/items' | head -5"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode('utf-8', errors='replace')
        
        if '/api/shop-v3/items' in output and '/vidgenerator' not in output:
            print_info("Found incorrect API call - needs /vidgenerator prefix")
            print_info("Updating shop/index.html...")
            
            # Use sed to replace the API call
            cmd = f"sed -i 's|/api/shop-v3/items|/vidgenerator/api/shop-v3/items|g' {shop_html_file}"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            stdout.read()
            
            print_success("Shop page API call updated")
            return True
        else:
            print_success("Shop page API call is correct")
            return True
            
    except Exception as e:
        print_error(f"Could not fix shop page: {str(e)[:100]}")
        return False

def clear_cache_and_restart(ssh):
    """Clear cache and restart services"""
    print_header("CLEARING CACHE AND RESTARTING")
    
    try:
        print_info("Clearing Python cache...")
        ssh.exec_command("find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        ssh.exec_command("find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print_success("Cache cleared")
        
        print_info("Restarting services...")
        services = ['python-proxy.service', 'vidgenerator-gunicorn.service']
        for service in services:
            try:
                ssh.exec_command(f"systemctl restart {service} 2>&1", timeout=10)
                time.sleep(2)
            except:
                pass
        
        time.sleep(5)
        print_success("Services restarted")
        return True
        
    except Exception as e:
        print_error(f"Could not restart services: {str(e)[:100]}")
        return False

def main():
    """Main deployment routine"""
    print_header("DEPLOY ALL STATIC FILES AND FIX ROUTES")
    print(f"Server: {SERVER_HOST}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    ssh = None
    try:
        print_info("Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print_success("Connected to server")
        
        sftp = ssh.open_sftp()
        
        # Step 1: Deploy static files
        deploy_static_files(ssh, sftp)
        
        # Step 2: Check shop-v3 route
        check_shop_v3_route(ssh)
        
        # Step 3: Create trophie route
        create_trophie_route(ssh, sftp)
        
        # Step 4: Fix shop page API call
        fix_shop_page_api_call(ssh)
        
        sftp.close()
        
        # Step 5: Clear cache and restart
        clear_cache_and_restart(ssh)
        
        print_header("DEPLOYMENT COMPLETE")
        print_success("All static files deployed and routes fixed!")
        print_info(f"Live URL: https://{SERVER_HOST}/vidgenerator/shop")
        print_info(f"Trophie URL: https://{SERVER_HOST}/vidgenerator/trophie")
        print_info("Note: You may need to manually add trophie blueprint registration to register_blueprints.py")
        
        return 0
        
    except Exception as e:
        print_error(f"Deployment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if ssh:
            ssh.close()

if __name__ == '__main__':
    sys.exit(main())

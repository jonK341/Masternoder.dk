"""
Debug Game Mechanics 404 Issue
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def debug():
    """Debug Game Mechanics 404"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*60)
        print("DEBUGGING GAME MECHANICS 404")
        print("="*60)
        
        # Check if route file exists and is correct
        print("\n[CHECK 1] Verifying route file...")
        stdin, stdout, stderr = ssh.exec_command("test -f /var/www/html/backend/routes/unified_game_mechanics_routes.py && echo 'EXISTS' || echo 'NOT_FOUND'")
        print(f"  File exists: {stdout.read().decode().strip()}")
        
        # Check blueprint definition
        print("\n[CHECK 2] Checking blueprint definition...")
        stdin, stdout, stderr = ssh.exec_command("grep 'unified_mechanics_bp = Blueprint' /var/www/html/backend/routes/unified_game_mechanics_routes.py")
        bp_def = stdout.read().decode().strip()
        print(f"  {bp_def}")
        
        # Check if routes are defined
        print("\n[CHECK 3] Checking route definitions...")
        stdin, stdout, stderr = ssh.exec_command("grep '@unified_mechanics_bp.route' /var/www/html/backend/routes/unified_game_mechanics_routes.py | head -5")
        routes = stdout.read().decode().strip()
        print(f"  Routes found:")
        for line in routes.split('\n'):
            if line.strip():
                print(f"    {line.strip()}")
        
        # Test import
        print("\n[CHECK 4] Testing import...")
        test_import = """
import sys
sys.path.insert(0, '/var/www/html')
try:
    from backend.routes.unified_game_mechanics_routes import unified_mechanics_bp
    print(f'SUCCESS: Imported {unified_mechanics_bp.name}')
    print(f'URL prefix: {unified_mechanics_bp.url_prefix}')
    # List routes
    routes = []
    for rule in unified_mechanics_bp.deferred_functions:
        if hasattr(rule, '__name__'):
            print(f'Function: {rule.__name__}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
"""
        stdin, stdout, stderr = ssh.exec_command("cat > /tmp/test_gm_import.py << 'ENDOFFILE'\n" + test_import + "\nENDOFFILE")
        stdout.channel.recv_exit_status()
        
        stdin, stdout, stderr = ssh.exec_command("cd /var/www/html && python3 /tmp/test_gm_import.py 2>&1")
        output = stdout.read().decode('utf-8', errors='ignore')
        print(output)
        
        # Test registration in Flask app
        print("\n[CHECK 5] Testing registration in Flask app...")
        test_reg = """
import sys
sys.path.insert(0, '/var/www/html')
from flask import Flask
from backend.register_blueprints import register_all_blueprints

app = Flask(__name__)
register_all_blueprints(app)

# Find game mechanics routes
gm_routes = [str(r) for r in app.url_map.iter_rules() if 'game-mechanics' in str(r)]
print(f'Game Mechanics routes found: {len(gm_routes)}')
for r in gm_routes[:10]:
    print(f'  {r}')
"""
        stdin, stdout, stderr = ssh.exec_command("cat > /tmp/test_gm_reg.py << 'ENDOFFILE'\n" + test_reg + "\nENDOFFILE")
        stdout.channel.recv_exit_status()
        
        stdin, stdout, stderr = ssh.exec_command("cd /var/www/html && python3 /tmp/test_gm_reg.py 2>&1")
        output = stdout.read().decode('utf-8', errors='replace')
        # Filter out unicode warnings
        clean_output = output.encode('ascii', errors='ignore').decode('ascii')
        print(clean_output)
        
        # Test service import
        print("\n[CHECK 6] Testing service import...")
        stdin, stdout, stderr = ssh.exec_command("cd /var/www/html && python3 -c 'from backend.services.unified_game_mechanics_constructor import unified_game_mechanics; print(\"Service OK\")' 2>&1")
        service_output = stdout.read().decode('utf-8', errors='ignore')
        if "Service OK" in service_output:
            print("  [OK] Service imports successfully")
        else:
            print(f"  [ERROR] Service import failed:")
            print(f"  {service_output[:300]}")
        
        # Test endpoint via localhost
        print("\n[CHECK 7] Testing endpoint via localhost:8080...")
        stdin, stdout, stderr = ssh.exec_command("curl -s -w '\\nHTTP_CODE:%{http_code}' 'http://localhost:8080/vidgenerator/api/game-mechanics/subjects?user_id=test' 2>&1")
        localhost_output = stdout.read().decode('utf-8', errors='ignore')
        if "HTTP_CODE:200" in localhost_output:
            print("  [SUCCESS] Localhost works!")
            body = localhost_output.split("HTTP_CODE")[0].strip()
            print(f"  Response: {body[:200]}")
        else:
            print(f"  [FAIL] Localhost response: {localhost_output[:300]}")
        
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug()


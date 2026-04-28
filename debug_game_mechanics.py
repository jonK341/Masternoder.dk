"""
Debug Game Mechanics Blueprint Registration
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def debug():
    """Debug Game Mechanics registration"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*60)
        print("DEBUGGING GAME MECHANICS REGISTRATION")
        print("="*60)
        
        # Test import
        print("\\n[TEST 1] Testing import...")
        stdin, stdout, stderr = ssh.exec_command("cd /var/www/html && python3 -c 'from backend.routes.unified_game_mechanics_routes import unified_mechanics_bp; print(f\"OK: {unified_mechanics_bp.name}\")' 2>&1")
        output = stdout.read().decode('utf-8', errors='ignore')
        print(output)
        
        # Check file exists
        print("\\n[TEST 2] Checking file...")
        stdin, stdout, stderr = ssh.exec_command("test -f /var/www/html/backend/routes/unified_game_mechanics_routes.py && echo 'EXISTS' || echo 'NOT_FOUND'")
        print(stdout.read().decode().strip())
        
        # Check blueprint definition
        print("\\n[TEST 3] Checking blueprint definition...")
        stdin, stdout, stderr = ssh.exec_command("grep 'unified_mechanics_bp = Blueprint' /var/www/html/backend/routes/unified_game_mechanics_routes.py")
        print(stdout.read().decode().strip())
        
        # Test registration
        print("\\n[TEST 4] Testing registration...")
        test_script = """
import sys
sys.path.insert(0, '/var/www/html')
from flask import Flask
try:
    from backend.routes.unified_game_mechanics_routes import unified_mechanics_bp
    app = Flask(__name__)
    app.register_blueprint(unified_mechanics_bp)
    routes = [str(r) for r in app.url_map.iter_rules() if 'game-mechanics' in str(r)]
    print(f"SUCCESS: {len(routes)} routes registered")
    for r in routes[:5]:
        print(f"  {r}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
"""
        stdin, stdout, stderr = ssh.exec_command("cat > /tmp/test_gm.py << 'ENDOFFILE'\n" + test_script + "\nENDOFFILE")
        stdout.channel.recv_exit_status()
        
        stdin, stdout, stderr = ssh.exec_command("cd /var/www/html && python3 /tmp/test_gm.py 2>&1")
        output = stdout.read().decode('utf-8', errors='ignore')
        print(output)
        
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    debug()


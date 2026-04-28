import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=20)

def run(cmd, t=30):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode('utf-8', errors='replace').strip(), err.read().decode('utf-8', errors='replace').strip()

# Try to import leaderboard_routes directly
o, e = run("""python3 -c "
import sys, os, traceback
sys.path.insert(0, '/var/www/html/vidgenerator')
sys.path.insert(0, '/var/www/html')
os.chdir('/var/www/html/vidgenerator')
os.environ.setdefault('FLASK_ENV', 'production')
try:
    from backend.routes.leaderboard_routes import leaderboard_bp
    print('OK - leaderboard_bp:', leaderboard_bp.name)
    print('deferred functions:', len(leaderboard_bp.deferred_functions))
    routes_in_bp = [f.func.__name__ if hasattr(f, 'func') else str(f) for f in leaderboard_bp.deferred_functions[:5]]
    print('sample funcs:', routes_in_bp)
except Exception as ex:
    print('IMPORT ERROR:', ex)
    traceback.print_exc()
" 2>&1""", t=25)
print("Leaderboard import test:", o)
print("Stderr:", e[:200] if e else "none")
print()

# Try to import shop_routes and check daily-deal
o, e = run("""python3 -c "
import sys, os
sys.path.insert(0, '/var/www/html/vidgenerator')
sys.path.insert(0, '/var/www/html')
os.chdir('/var/www/html/vidgenerator')
try:
    from backend.routes.shop_routes import shop_bp
    # list all routes
    from inspect import getmembers, isfunction
    # count deferred
    print('shop_bp deferred:', len(shop_bp.deferred_functions))
    print('shop_bp file:', sys.modules['backend.routes.shop_routes'].__file__)
    # check if daily-deal is registered
    import backend.routes.shop_routes as sm
    has_dd = hasattr(sm, 'shop_daily_deal') or 'daily' in open(sm.__file__).read()
    print('has daily-deal:', has_dd)
except Exception as ex:
    print('IMPORT ERROR:', ex)
" 2>&1""", t=25)
print("Shop import test:", o)

import os
ssh.close()

import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=20)

def run(cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode('utf-8', errors='replace').strip()

o = run("grep -n 'daily.deal\\|shop_bp\\|recommendations' /var/www/html/backend/routes/shop_routes.py | head -10")
print("ROOT shop_routes.py:", o)
print()
o = run("grep -n 'daily.deal\\|shop_bp\\|recommendations' /var/www/html/vidgenerator/backend/routes/shop_routes.py | head -10")
print("VIDGEN shop_routes.py:", o)
print()
o = run("grep -n 'leaderboard_routes\\|leaderboard_bp' /var/www/html/backend/register_blueprints.py | head -5")
print("ROOT register_blueprints leaderboard:", o)
print()
o = run("grep -n 'shop_bp\\|shop_routes' /var/www/html/backend/register_blueprints.py | head -5")
print("ROOT register_blueprints shop:", o)
print()

# What blueprints are actually registered in the live app?
o = run(r"""python3 -c "
import sys, os
sys.path.insert(0, '/var/www/html/vidgenerator')
sys.path.insert(0, '/var/www/html')
os.chdir('/var/www/html/vidgenerator')
from src.app import create_app
app = create_app()
shop_routes = [str(r) for r in app.url_map.iter_rules() if 'shop' in str(r) and 'daily' in str(r)]
lb_routes = [str(r) for r in app.url_map.iter_rules() if 'leaderboard' in str(r) and 'top' in str(r)]
print('shop daily routes:', shop_routes)
print('leaderboard top routes:', lb_routes)
" 2>&1 | grep -E "shop|leaderboard|ERROR"
""", t=30)
print("App route check:", o)

import os
ssh.close()

import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=20)

def run(cmd, t=30):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode().strip(), err.read().decode().strip()

o, _ = run(r"""python3 -c "
import sys
sys.path.insert(0, '/var/www/html/vidgenerator')
sys.path.insert(0, '/var/www/html')
# Simulate what wsgi.py does
import os
os.chdir('/var/www/html/vidgenerator')
from src.app import create_app
app = create_app()
# Print sys.path after app creation
print('PATHS:', sys.path[:6])
# Find leaderboard
found = [str(r) for r in app.url_map.iter_rules() if 'leaderboard' in str(r)][:3]
print('LEADERBOARD:', found)
" 2>&1 | grep -E "PATHS|LEADERBOARD|ERROR"
""", t=30)
print("Result:", o)
print()

# Also check if /var/www/html/vidgenerator is on Python path in the actual running process
o, _ = run("cat /var/www/html/vidgenerator/wsgi.py | head -20")
print("wsgi.py:")
print(o)
ssh.close()

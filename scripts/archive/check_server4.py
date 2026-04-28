import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password='eD)2[K+[S#m_#$3!', timeout=20)

def run(cmd, t=20):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode().strip(), err.read().decode().strip()

# List ALL registered /api/system routes via Flask's route map
test_cmd = """python3 - << 'EOF'
import sys
sys.path.insert(0, '/var/www/html')
from src.app import create_app
app = create_app()
routes = [str(rule) for rule in app.url_map.iter_rules() if 'system' in str(rule)]
print('Routes with system:', routes)
for rule in app.url_map.iter_rules():
    if 'overview' in str(rule) or 'system_overview' in rule.endpoint:
        print('  FOUND:', rule, '->', rule.endpoint)
EOF"""
o, e = run(test_cmd, t=30)
print("Flask route map:")
print(o[:1000])
if e:
    print("STDERR:", e[:500])

# Check for duplicate endpoint error in uwsgi
o, _ = run("journalctl -u uwsgi -n 50 | grep -i 'assert\\|duplicate\\|overlap\\|system_overview\\|overview' | head -20")
print("\nuwsgi logs:", o or "(none)")

ssh.close()

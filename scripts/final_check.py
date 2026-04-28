import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=30)

def run(cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode('utf-8', errors='replace').strip()

status = run('systemctl is-active uwsgi-vidgenerator', t=8)
print('Service:', status)
if status not in ('active', 'activating'):
    print('Starting...')
    run('systemctl start uwsgi-vidgenerator', t=10)
    time.sleep(12)
    status = run('systemctl is-active uwsgi-vidgenerator', t=5)
    print('Service now:', status)

endpoints = [
    '/vidgenerator/api/system/overview?compact=1',
    '/vidgenerator/api/leaderboard/top10',
    '/vidgenerator/api/leaderboard',
    '/vidgenerator/api/quests/daily',
    '/vidgenerator/api/shop/daily-deal',
    '/vidgenerator/api/agent/automation/ai-diagnose',
]
for ep in endpoints:
    code = run(f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{ep}' --max-time 12", t=20)
    print(f"  {'[OK]' if code == '200' else '[WARN]'}  {ep} -> {code}")

import os
ssh.close()

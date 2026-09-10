#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""
echo '== uwsgi unit =='
systemctl cat uwsgi-vidgenerator 2>&1 | head -40
echo '== wsgi via uwsgi module test =='
cd /var/www/html
python3 <<'PY'
import os, sys
os.chdir('/var/www/html')
sys.path.insert(0, '/var/www/html')
import wsgi
app = wsgi.application
print('creator in blueprints:', 'creator' in app.blueprints)
print('rules:', [r.rule for r in app.url_map.iter_rules() if 'creator' in r.rule][:5])
PY
"""

ssh, _, _ = connect_deploy_ssh()
stdin, stdout, stderr = ssh.exec_command(REMOTE, timeout=90)
print((stdout.read() + stderr.read()).decode(errors="replace"))
ssh.close()

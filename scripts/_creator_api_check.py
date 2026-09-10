#!/usr/bin/env python3
"""Remote check: creator API + blueprint import on server."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""
cd /var/www/html || exit 1
echo '== import creator_bp =='
python3 -c 'from backend.routes.creator_routes import creator_bp; print("routes", len(creator_bp.deferred_functions))' 2>&1
echo '== LITE_APP env =='
grep LITE_APP /var/www/html/.env 2>/dev/null || echo 'no LITE_APP in .env'
echo '== create_app blueprints =='
python3 <<'PY'
import os, sys
os.chdir("/var/www/html")
sys.path.insert(0, "/var/www/html")
from src.app import create_app
app = create_app()
print("creator registered:", "creator" in app.blueprints)
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    if "/api/creator" in rule.rule:
        print(rule.rule)
PY
echo '== curl :5000 =='
curl -sS -m 10 http://127.0.0.1:5000/api/creator/config 2>&1 | head -c 500
echo
echo '== curl :5001 =='
curl -sS -m 10 http://127.0.0.1:5001/api/creator/config 2>&1 | head -c 500
echo
echo '== grep creator_routes =='
grep -n 'creator_routes\|Registered creator' backend/register_blueprints.py 2>/dev/null | head -10
echo '== uwsgi restart =='
systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>&1
sleep 4
curl -sS -m 10 http://127.0.0.1:5000/api/creator/config 2>&1 | head -c 500
echo
"""

ssh, _auth, _pw = connect_deploy_ssh()
stdin, stdout, stderr = ssh.exec_command(REMOTE, timeout=60)
print((stdout.read() + stderr.read()).decode(errors="replace"))
ssh.close()

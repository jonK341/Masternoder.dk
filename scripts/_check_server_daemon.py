#!/usr/bin/env python3
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

ssh, _, _ = connect_deploy_ssh(require_deploy_pass())
time.sleep(75)
cmd = (
    "cd /var/www/html && LITE_APP=1 DAEMON_QUIET=1 python3 -c "
    "'from backend.services.profit_daemon_monitor_service import monitor_status; "
    "import json; print(json.dumps(monitor_status()))'"
)
_, o, _ = ssh.exec_command(cmd, timeout=120)
print(o.read().decode("ascii", errors="replace")[:3000])
_, o2, _ = ssh.exec_command("tail -n 5 /var/www/html/logs/profit_daemon_stdout.log", timeout=30)
print("--- log ---")
print(o2.read().decode("ascii", errors="replace"))
ssh.close()

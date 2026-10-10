import sys
sys.path.insert(0, r"c:\Users\jonkh\UsecaseSampler\Masternoder.dk")
from deploy_ssh_env import connect_deploy_ssh
REMOTE = """
grep -i "work queue" /var/www/html/config/debug.log 2>/dev/null | tail -15
grep -i "work queue" /var/www/html/logs/*.log 2>/dev/null | tail -5
wc -l /var/www/html/config/debug.log
"""
ssh, _, _ = connect_deploy_ssh(timeout=60)
_, stdout, _ = ssh.exec_command(REMOTE, timeout=60)
print(stdout.read().decode(errors="replace").encode("ascii","backslashreplace").decode())
ssh.close()

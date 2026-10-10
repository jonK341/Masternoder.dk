import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass
ssh, _, _ = connect_deploy_ssh(require_deploy_pass())
_, stdout, _ = ssh.exec_command("curl -s --max-time 25 'https://127.0.0.1/api/mn2/deposit-address?user_id=platform_treasury' -H 'Host: masternoder.dk' -k", timeout=40)
print(stdout.read().decode(errors="replace"))
ssh.close()

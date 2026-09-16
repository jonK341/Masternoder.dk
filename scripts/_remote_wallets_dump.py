import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import connect_deploy_ssh, _load_deploy_env_from_dotenv
_load_deploy_env_from_dotenv()
ssh, _, _ = connect_deploy_ssh(os.environ["DEPLOY_PASS"])
for path in [
    "ls /var/www/html/data/crypto_exchange/agent_accounts/ 2>&1 | head -20",
    "ls /var/www/html/data/crypto_exchange/wallets/ 2>&1",
]:
    _, o, _ = ssh.exec_command(path, timeout=30)
    print(">>>", path)
    print(o.read().decode())
ssh.close()

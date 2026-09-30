import sys
sys.path.insert(0, ".")
from deploy_ssh_env import connect_deploy_ssh
ssh, auth, _ = connect_deploy_ssh(timeout=60)
cmd = """cd /var/www/html
python3 -c 'import cryptography; print("sys_crypto_ok")' 2>&1
.venv/bin/python -c 'import cryptography; print("venv_crypto_ok")' 2>&1
grep -q EXCHANGE_VAULT_KEY .env && echo vault_key_in_env=yes || echo vault_key_in_env=no
python3 scripts/remote_vault_import.py 2>&1 | tail -2
"""
_, o, _ = ssh.exec_command(cmd, timeout=90)
print("auth:", auth)
print(o.read().decode())
ssh.close()

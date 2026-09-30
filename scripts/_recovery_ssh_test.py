import sys
sys.path.insert(0, r"c:\Users\jonkh\UsecaseSampler\Masternoder.dk")
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

host = deploy_host()
user = deploy_user()
print(f"Connecting to {user}@{host} ...", flush=True)
try:
    ssh, auth, _ = connect_deploy_ssh(timeout=45)
    print(f"SSH OK via {auth}", flush=True)
    _, stdout, stderr = ssh.exec_command("echo CONNECTED; hostname; uptime", timeout=30)
    print(stdout.read().decode(errors="replace"), end="")
    err = stderr.read().decode(errors="replace")
    if err.strip():
        print("STDERR:", err, file=sys.stderr)
    ssh.close()
except SystemExit:
    raise
except Exception as e:
    print(f"SSH failed: {type(e).__name__}: {e}")
    sys.exit(1)

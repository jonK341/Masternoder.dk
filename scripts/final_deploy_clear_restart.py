"""Clear pycache at correct root and do clean restart."""
import paramiko, os, time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
SERVER_ROOT = "/var/www/html"

def run(ssh, cmd, timeout=30):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

print("=== Clearing ALL pycache in server root ===")
print(run(ssh, f"find {SERVER_ROOT}/backend {SERVER_ROOT}/src -name '__pycache__' -type d -exec rm -rf {{}} + 2>/dev/null && find {SERVER_ROOT}/backend {SERVER_ROOT}/src -name '*.pyc' -delete 2>/dev/null && echo cleared"))

print("\n=== Hard restart uWSGI ===")
print(run(ssh, "systemctl stop uwsgi && sleep 3 && systemctl start uwsgi && echo restarted", timeout=40))
time.sleep(10)

print("Status:", run(ssh, "systemctl is-active uwsgi"))

print("\n=== Check startup log for agent_profile ===")
print(run(ssh, f"tail -30 {SERVER_ROOT}/vidgenerator/uwsgi.log 2>/dev/null | grep -E 'agent_profile|SUMMARY'"))

print("\n=== Live test ===")
r1 = run(ssh, "curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/my-agents?user_id=default_user' 2>&1 | head -c 500")
print("my-agents:", r1)

ssh.close()
print("Done.")

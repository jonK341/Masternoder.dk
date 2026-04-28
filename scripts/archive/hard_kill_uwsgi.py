"""Kill old uwsgi master directly and start fresh."""
import paramiko, os, time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run(ssh, cmd, timeout=30):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())\

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

print("=== Before kill ===")
print(run(ssh, "ps aux | grep 'uwsgi' | grep -v grep"))

print("\n=== Killing all uwsgi processes ===")
print(run(ssh, "pkill -9 -f uwsgi && sleep 3 && echo killed"))

print("After kill:")
print(run(ssh, "ps aux | grep 'uwsgi' | grep -v grep"))

print("\n=== Starting fresh uwsgi via init.d ===")
print(run(ssh, "/etc/init.d/uwsgi start 2>&1 && echo started"))
time.sleep(8)

print("\n=== Verify new processes ===")
print(run(ssh, "ps aux | grep 'uwsgi' | grep -v grep"))

print("\n=== Test agent endpoint ===")
r = run(ssh, "curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/my-agents?user_id=default_user' 2>&1 | head -c 500")
print(r)

ssh.close()
print("Done.")

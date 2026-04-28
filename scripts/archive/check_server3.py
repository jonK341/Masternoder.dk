import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password='eD)2[K+[S#m_#$3!', timeout=20)

def run(cmd, t=20):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode().strip(), err.read().decode().strip()

# Force a full restart
print("Force restarting uwsgi...")
o, e = run("systemctl stop uwsgi && sleep 2 && systemctl start uwsgi", t=20)
print(f"  stop/start: {o[:100]} | err: {e[:100]}")
time.sleep(8)

# Check if started
o, _ = run("systemctl is-active uwsgi")
print(f"  uwsgi active: {o}")

# Test the endpoint
o, _ = run("curl -s 'http://localhost:5000/api/system/overview?compact=1' --max-time 10 -w ' STATUS:%{http_code}'")
print(f"  localhost test: {o[:300]}")

# Check for any Flask errors during startup
o, _ = run("journalctl -u uwsgi --since '20 sec ago' | grep -i 'error\\|Error\\|warning\\|Warning' | head -10")
print(f"  uwsgi errors: {o or '(none)'}")

ssh.close()

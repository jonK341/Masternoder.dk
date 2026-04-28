import paramiko, time, subprocess, sys, os

HOST, USER, PASS = os.environ.get("DEPLOY_HOST", "masternoder.dk"), os.environ.get("DEPLOY_USER", "root"), (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def new_ssh():
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    s.connect(HOST, username=USER, password=PASS, timeout=30)
    return s

def run(s, cmd, t=20):
    _, o, _ = s.exec_command(cmd, timeout=t)
    return o.read().decode("utf-8", errors="replace").strip()

print("Polling until uwsgi-vidgenerator is fully active and stable...")
for i in range(20):
    ssh = new_ssh()
    s = run(ssh, "systemctl is-active uwsgi-vidgenerator", t=5)
    workers = run(ssh, "ps aux | grep 'uwsgi.*vidgenerator' | grep -v grep | wc -l", t=5)
    print(f"  [{i+1:2d}] status={s:12s}  workers={workers}")
    ssh.close()
    if s == "active" and int(workers) >= 4:
        print("  Service stable!")
        break
    time.sleep(5)

import os
print("\nRunning final verification...")
BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(os.path.dirname(BASE))
result = subprocess.run([sys.executable, os.path.join(BASE, "final_verify.py")], capture_output=False)

"""Restart uWSGI on the server."""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

ssh.exec_command("service uwsgi restart")
time.sleep(4)
stdin, stdout, stderr = ssh.exec_command("ps aux | grep uwsgi | grep -v grep | wc -l")
print(f"uWSGI workers: {stdout.read().decode().strip()}")

import os
ssh.close()
print("Done.")

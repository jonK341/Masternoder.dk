#!/usr/bin/env python3
import os
import paramiko

HOST = "masternoder.dk"
USER = "root"
PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
DOC_ID = os.getenv("DOC_ID", "4b52aa40-043f-4fa0-81e8-7d454928496f")

COMMANDS = [
    ("ffmpeg", "which ffmpeg; ffmpeg -version | sed -n '1,2p'"),
    ("videos_dir", "ls -la /var/www/html/vidgenerator/videos | tail -n 20"),
    ("doc_files", f"ls -la /var/www/html/vidgenerator/videos/{DOC_ID}* 2>/dev/null || true"),
    ("doc_status", f"sed -n '1,120p' /var/www/html/vidgenerator/videos/{DOC_ID}.status.json 2>/dev/null || true"),
    ("ffmpeg_proc", "ps -eo pid,comm,etime,pcpu,pmem,args | egrep 'ffmpeg|uwsgi' | tail -n 40"),
    ("uwsgi_log", "journalctl -u uwsgi -n 120 --no-pager"),
    ("proxy_log", "journalctl -u python-proxy -n 80 --no-pager"),
]


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=HOST, username=USER, password=PASS, timeout=20)
    try:
        for name, cmd in COMMANDS:
            print("\n" + "=" * 12 + f" {name} " + "=" * 12)
            _stdin, stdout, stderr = ssh.exec_command(cmd, timeout=90)
            out = stdout.read().decode("utf-8", "ignore")
            err = stderr.read().decode("utf-8", "ignore")
            print(out[:15000] if out else "(no stdout)")
            if err.strip():
                print("--- stderr ---")
                print(err[:3000])
    finally:
        ssh.close()


if __name__ == "__main__":
    main()


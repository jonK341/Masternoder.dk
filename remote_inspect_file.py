#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick remote file inspector for masternoder.dk (via paramiko).
Prints the first N lines of a remote file.
"""
import os
import sys
import paramiko

HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USER = os.getenv("DEPLOY_USER", "root")
PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def main():
    if len(sys.argv) < 2:
        print("Usage: python remote_inspect_file.py /remote/path [lines=120]")
        sys.exit(2)

    remote_path = sys.argv[1]
    lines = int(sys.argv[2]) if len(sys.argv) >= 3 else 120

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    cmd = f"sed -n '1,{lines}p' {remote_path}"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    print(out)
    if err.strip():
        print("--- STDERR ---")
        print(err)
    ssh.close()

if __name__ == "__main__":
    main()


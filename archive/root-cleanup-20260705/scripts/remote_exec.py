#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remote command runner for masternoder.dk (via paramiko).
Usage: python remote_exec.py "command"
"""
import os
import sys
import paramiko

HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USER = os.getenv("DEPLOY_USER", "root")
PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def main():
    if len(sys.argv) < 2:
        print("Usage: python remote_exec.py \"command\"")
        sys.exit(2)
    cmd = sys.argv[1]
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    safe_out = out.encode("ascii", "backslashreplace").decode("ascii")
    safe_err = err.encode("ascii", "backslashreplace").decode("ascii")
    print(safe_out)
    if safe_err.strip():
        print("--- STDERR ---")
        print(safe_err)
    ssh.close()

if __name__ == "__main__":
    main()


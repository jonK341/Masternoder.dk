#!/usr/bin/env python3
"""Verify micro-tx endpoints on production (localhost via SSH)."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from deploy_ssh_env import connect_deploy_ssh

ssh, _auth, _pw = connect_deploy_ssh()
paths = [
    "/api/mn2/micro-tx/config",
    "/api/mn2/micro-tx/stats",
]
for port in (5000, 5001):
    print(f"--- port {port} ---")
    for path in paths:
        cmd = f"curl -sS -m 20 -w '\\nHTTP:%{{http_code}}' 'http://127.0.0.1:{port}{path}'"
        _i, stdout, stderr = ssh.exec_command(cmd, timeout=30)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        print(f"=== {path} ===")
        print(out[:800])
        if err.strip():
            print("stderr:", err[:200])
ssh.close()

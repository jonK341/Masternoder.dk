#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnose 404 - check what's actually serving :5000."""
import os
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def sh(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out + ("\n" + err if err else "")


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    print("=" * 60)
    print("DIAGNOSE 404 - WHAT'S SERVING :5000?")
    print("=" * 60)

    print("\n[1] What process listens on :5000?")
    print(sh(ssh, "ss -ltnp | grep ':5000' 2>/dev/null || netstat -tlnp | grep ':5000' 2>/dev/null"))

    print("\n[2] python-proxy service details:")
    print(sh(ssh, "systemctl status python-proxy --no-pager -l | head -25"))

    print("\n[3] uwsgi-vidgenerator service details:")
    print(sh(ssh, "systemctl status uwsgi-vidgenerator --no-pager -l | head -25"))

    print("\n[4] Check python-proxy.service file:")
    print(sh(ssh, "cat /etc/systemd/system/python-proxy.service 2>/dev/null || cat /lib/systemd/system/python-proxy.service 2>/dev/null || echo 'not found'"))

    print("\n[5] Check uwsgi-vidgenerator config:")
    print(sh(ssh, "cat /etc/uwsgi/apps-enabled/vidgenerator.ini 2>/dev/null | head -30"))

    print("\n[6] Test a known working route:")
    print("  /vidgenerator/api/health:", sh(ssh, "curl -s http://127.0.0.1:5000/api/health 2>/dev/null | head -c 200"))
    print("  /api/health:", sh(ssh, "curl -s http://127.0.0.1:5000/api/health 2>/dev/null | head -c 200"))

    print("\n[7] Test via nginx (public path):")
    print("  /vidgenerator/api/health:", sh(ssh, "curl -s http://127.0.0.1/vidgenerator/api/health 2>/dev/null | head -c 200"))

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

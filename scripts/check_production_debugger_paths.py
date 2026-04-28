#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check which debugger index.html path production serves.
"""
import os
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def _read_remote(sftp: paramiko.SFTPClient, path: str) -> str:
    with sftp.open(path, "r") as f:
        data = f.read()
    try:
        return data.decode("utf-8", errors="replace")
    except AttributeError:
        # already str
        return data


def main() -> None:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    sftp = ssh.open_sftp()
    try:
        paths = [
            "/var/www/html/vidgenerator/debugger/index.html",
            "/var/www/html/vidgenerator/vidgenerator/debugger/index.html",
            "/var/www/html/vidgenerator/src/web/debugger/index.html",
        ]
        print("=" * 70)
        print("PRODUCTION DEBUGGER FILE PATH CHECK")
        print("=" * 70)
        for p in paths:
            try:
                txt = _read_remote(sftp, p)
                print(f"\n{p}")
                print(f"  size={len(txt)} has_cache_version={'cache-version' in txt} has_aggressive={'AGGRESSIVE CACHE-BUSTING' in txt}")
                print(f"  head={txt[:140].replace('\\n','\\\\n')}")
            except Exception as e:
                print(f"\n{p}\n  MISSING/ERROR: {e}")
    finally:
        try:
            sftp.close()
        except Exception:
            pass
        ssh.close()


if __name__ == "__main__":
    main()


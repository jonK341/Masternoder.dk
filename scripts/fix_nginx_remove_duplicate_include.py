#!/usr/bin/env python3
"""Remove the vidgenerator-api-proxy include we added (causes duplicate location)."""
import os
import sys

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def run():
    try:
        import paramiko
    except ImportError:
        print("Install paramiko")
        return False
    ssh = None
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        config_file = "/etc/nginx/sites-available/masternoder.dk"
        stdin, stdout, stderr = ssh.exec_command(f"cat {config_file}", timeout=10)
        config = stdout.read().decode("utf-8", errors="replace")
        # Remove our include line
        lines = config.split("\n")
        new_lines = [L for L in lines if "vidgenerator-api-proxy" not in L]
        if len(new_lines) != len(lines):
            new_config = "\n".join(new_lines)
            sftp = ssh.open_sftp()
            with sftp.open(config_file, "w") as f:
                f.write(new_config)
            sftp.close()
            print("Removed duplicate include")
        stdin, stdout, stderr = ssh.exec_command("nginx -t 2>&1", timeout=10)
        out = (stdout.read() + stderr.read()).decode("utf-8", errors="replace")
        if "syntax is ok" in out.lower():
            ssh.exec_command("systemctl reload nginx 2>&1", timeout=15)
            print("Nginx reloaded OK")
            return True
        else:
            print("Nginx config error:", out[:300])
            return False
    except Exception as e:
        print("ERROR:", e)
        return False
    finally:
        if ssh:
            ssh.close()

if __name__ == "__main__":
    sys.exit(0 if run() else 1)

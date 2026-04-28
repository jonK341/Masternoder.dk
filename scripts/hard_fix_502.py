#!/usr/bin/env python3
"""Hard fix 502: kill uwsgi, add nginx timeouts, restart, verify."""
import os
import sys
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
NGINX_SITE = "/etc/nginx/sites-enabled/masternoder.dk"

def run(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace").strip()
    err = stderr.read().decode(errors="replace").strip()
    return out, err

def main():
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    print("=" * 60)
    print("HARD FIX 502")
    print("=" * 60)

    # 1. Kill uwsgi forcefully
    print("\n[1] Killing all uwsgi")
    run(ssh, "systemctl stop uwsgi-vidgenerator 2>/dev/null; systemctl stop uwsgi 2>/dev/null; sleep 2; pkill -9 -f uwsgi 2>/dev/null; sleep 3; echo done")
    out, _ = run(ssh, "ps aux | grep uwsgi | grep -v grep || echo 'no uwsgi'")
    print(f"  {out[:200] if out else 'none'}")

    # 2. Add nginx proxy timeouts if missing
    print("\n[2] Nginx proxy timeouts")
    out, _ = run(ssh, f"grep -c proxy_read_timeout {NGINX_SITE} 2>/dev/null || echo 0")
    if "0" in out or not out:
        run(ssh, f"cp {NGINX_SITE} {NGINX_SITE}.bak")
        # Add timeout lines after each proxy_set_header X-Forwarded-Proto
        run(ssh, f"awk '/proxy_set_header X-Forwarded-Proto/ {{ print; print \"        proxy_connect_timeout 30;\"; print \"        proxy_send_timeout 120;\"; print \"        proxy_read_timeout 120;\"; next }} 1' {NGINX_SITE}.bak > {NGINX_SITE}")
        tst, _ = run(ssh, "nginx -t 2>&1")
        if "ok" in tst.lower():
            run(ssh, "systemctl reload nginx")
            print("  Added proxy_read_timeout 120s, reloaded nginx")
        else:
            run(ssh, f"mv {NGINX_SITE}.bak {NGINX_SITE}")
            print(f"  nginx -t failed, reverted: {tst[:80]}")
    else:
        print("  Timeouts already present")

    # 3. Start uwsgi-vidgenerator (single service, see docs/DEPLOYMENT_PLAN.md)
    print("\n[3] Starting uwsgi-vidgenerator")
    run(ssh, "systemctl start uwsgi-vidgenerator", timeout=15)
    time.sleep(12)
    out, _ = run(ssh, "systemctl is-active uwsgi-vidgenerator")
    print(f"  uwsgi-vidgenerator: {out}")

    # 4. Test port 5000 (with timeout)
    print("\n[4] Testing port 5000")
    out, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' --max-time 20 http://127.0.0.1:5000/ 2>/dev/null || echo 'timeout'")
    print(f"  Port 5000: HTTP {out}")

    # 5. Test HTTPS
    print("\n[5] Testing HTTPS")
    out, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' --max-time 25 https://masternoder.dk/ 2>/dev/null || echo 'timeout'")
    print(f"  HTTPS: HTTP {out}")

    ssh.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

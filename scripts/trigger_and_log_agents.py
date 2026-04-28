"""Trigger /agents/ request and immediately read full error."""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run_cmd(ssh, cmd, timeout=20):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    # Get log size before
    out = run_cmd(ssh, f"wc -l {BASE_REMOTE}/uwsgi.log 2>/dev/null")
    print(f"Log lines before: {out}")

    # Trigger the request on localhost (bypassing nginx/HTTPS)
    print("Triggering /vidgenerator/agents/...")
    out = run_cmd(ssh, "curl -s http://127.0.0.1:5000/vidgenerator/agents/ 2>/dev/null | head -5 || curl -s --unix-socket /var/www/html/vidgenerator/uwsgi.sock http://localhost/vidgenerator/agents/ 2>/dev/null | head -5 || echo 'direct socket not available'", timeout=10)
    print(f"Direct result: {out[:200]}")

    # Also try via nginx
    out = run_cmd(ssh, "curl -sk https://masternoder.dk/vidgenerator/agents/ 2>/dev/null | head -5")
    print(f"nginx result: {out[:200]}")
    time.sleep(1)

    # Read new log lines
    print("\n--- New log lines ---")
    out = run_cmd(ssh, f"tail -30 {BASE_REMOTE}/uwsgi.log 2>/dev/null")
    print(out)

    # Check if agents_page function is registered
    print("\n--- agents_page in routes ---")
    out = run_cmd(ssh, f"grep -n 'agents_page\\|def agents' {BASE_REMOTE}/backend/routes/all_page_routes.py")
    print(out)

    # Python check
    print("\n--- Python verify ---")
    out = run_cmd(ssh, f"cd {BASE_REMOTE} && .venv/bin/python -c \"from backend.routes.all_page_routes import all_page_bp; print('routes:', [r.rule for r in all_page_bp.deferred_functions][:3] if hasattr(all_page_bp, 'deferred_functions') else 'n/a')\" 2>&1 | tail -5")
    print(out)

    ssh.close()

if __name__ == '__main__':
    main()

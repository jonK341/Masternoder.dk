"""Verify agent system deployment and service status."""
import paramiko
import time
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    time.sleep(3)

    out, _ = run_cmd(ssh, "systemctl is-active vidgenerator 2>/dev/null || echo unknown")
    print(f"Service status: {out}")

    out, _ = run_cmd(ssh, "ps aux | grep -c uwsgi | tr -d ' '")
    print(f"uWSGI processes: {out}")

    # Check agents page exists
    out, _ = run_cmd(ssh, "test -f /var/www/html/vidgenerator/vidgenerator/agents/index.html && echo 'agents page: OK' || echo 'agents page: MISSING'")
    print(out)

    # Check agent_profile_routes registered
    out, _ = run_cmd(ssh, "grep -c 'agent_profile' /var/www/html/vidgenerator/backend/register_blueprints.py")
    print(f"agent_profile in register_blueprints: {out} lines")

    # Quick HTTP check
    out, _ = run_cmd(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost/vidgenerator/agents/ 2>/dev/null || echo 'no local curl'")
    print(f"HTTP /agents/: {out}")

    out, _ = run_cmd(ssh, "curl -s -o /dev/null -w '%{http_code}' 'http://localhost/vidgenerator/api/agents/my-agents?user_id=default_user' 2>/dev/null || echo 'no local curl'")
    print(f"HTTP /api/agents/my-agents: {out}")

    ssh.close()

if __name__ == "__main__":
    main()

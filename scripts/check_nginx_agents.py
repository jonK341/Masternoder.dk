"""Check nginx config and error log for /agents/ 500."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=20):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    print("=== nginx error log (last 20 lines) ===")
    out = run_cmd(ssh, "tail -20 /var/log/nginx/error.log 2>/dev/null")
    print(out)

    print("\n=== nginx sites-enabled for masternoder ===")
    out = run_cmd(ssh, "cat /etc/nginx/sites-enabled/masternoder.dk 2>/dev/null || cat /etc/nginx/sites-enabled/default 2>/dev/null | head -60")
    print(out)

    print("\n=== Test curl directly via uWSGI socket ===")
    out = run_cmd(ssh, "curl -s --unix-socket /var/www/html/vidgenerator/vidgenerator.sock http://localhost/vidgenerator/agents/ 2>/dev/null | head -3 || echo 'sock not found, trying port...'")
    print(out)
    out = run_cmd(ssh, "curl -s http://127.0.0.1:5000/vidgenerator/agents/ 2>/dev/null | head -3 || echo 'port 5000 not available'")
    print(out)

    # Check what socket uWSGI is bound to
    print("\n=== uWSGI socket/port ===")
    out = run_cmd(ssh, "grep -E 'socket|http' /var/www/html/vidgenerator/uwsgi.ini 2>/dev/null")
    print(out)

    ssh.close()

if __name__ == '__main__':
    main()

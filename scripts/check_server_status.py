"""Check service status and recent generation errors on production server."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode().strip(), stderr.read().decode().strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)

    print("=== Running processes ===")
    out, _ = run_cmd(ssh, "ps aux | grep -E 'python|gunicorn' | grep -v grep | head -10")
    print(out or "(none)")

    print("\n=== Systemd service status ===")
    out, _ = run_cmd(ssh, "systemctl list-units | grep -i vid | head -5")
    print(out or "(none)")
    out, _ = run_cmd(ssh, "systemctl status vidgenerator 2>/dev/null | head -15")
    print(out or "(not found)")

    print("\n=== Service file contents ===")
    out, _ = run_cmd(ssh, "cat /etc/systemd/system/vidgenerator.service 2>/dev/null")
    print(out or "(not found)")

    print("\n=== Recent error logs ===")
    out, _ = run_cmd(ssh, "journalctl -u vidgenerator --no-pager -n 30 2>/dev/null | tail -30")
    print(out or "(no logs)")

    print("\n=== How the 19:55 video was generated? ===")
    vid = "71449282-46b8-4bf4-92ab-2746676b62b3"
    out, _ = run_cmd(ssh, f"cat /var/www/html/vidgenerator/videos/{vid}.pipeline.json 2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin); print(\"title:\",d.get(\"title\")); print(\"user_id:\",d.get(\"user_id\")); print(\"segments:\",len(d.get(\"rearranged_segments\",[])))'")
    print(out or "(no pipeline json)")

    ssh.close()

if __name__ == "__main__":
    main()

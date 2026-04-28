"""Check for recent video generation failures on production server."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)

    print("=== Small/failed videos (< 100KB) ===")
    out, _ = run_cmd(ssh, "find /var/www/html/vidgenerator/videos -name '*.mp4' -size -100k -ls 2>/dev/null | sort -k8 -r | head -20")
    print(out or "(none)")

    print("\n=== All videos with durations ===")
    out, _ = run_cmd(ssh, "ls -t /var/www/html/vidgenerator/videos/*.mp4 2>/dev/null | head -20 | xargs -I{} sh -c 'printf \"%s %s: \" \"$(stat -c%s {})\" \"$(basename {})\"; ffprobe -v quiet -show_entries format=duration -of csv=p=0 \"{}\" 2>/dev/null; echo'")
    print(out or "(none)")

    print("\n=== uWSGI error log (last 50 lines) ===")
    out, _ = run_cmd(ssh, "tail -50 /var/www/html/vidgenerator/uwsgi.log 2>/dev/null")
    print(out or "(not found)")

    print("\n=== Nohup output (last 30 lines) ===")
    out, _ = run_cmd(ssh, "tail -30 /var/www/html/vidgenerator/nohup.out 2>/dev/null || echo '(not found)'")
    print(out)

    print("\n=== Fix: Stop broken Gunicorn service ===")
    out, _ = run_cmd(ssh, "systemctl stop vidgenerator-gunicorn 2>&1")
    print("Stopped:", out or "ok")

    out, _ = run_cmd(ssh, "systemctl disable vidgenerator-gunicorn 2>&1")
    print("Disabled:", out or "ok")

    ssh.close()

if __name__ == "__main__":
    main()

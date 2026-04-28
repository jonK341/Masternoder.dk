"""Verify the video fix is deployed and working."""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    time.sleep(3)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    print("=== uWSGI service status ===")
    out, _ = run_cmd(ssh, "systemctl is-active uwsgi-vidgenerator 2>/dev/null")
    print("Active:", out)

    print("\n=== Small videos remaining ===")
    out, _ = run_cmd(ssh, "find /var/www/html/vidgenerator/videos -name '*.mp4' -size -1024c 2>/dev/null | wc -l")
    print(f"Count: {out} (should be 0)")

    print("\n=== Stuck processing jobs ===")
    out, _ = run_cmd(ssh, "grep -l '\"status\": \"processing\"' /var/www/html/vidgenerator/videos/*.status.json 2>/dev/null | wc -l")
    print(f"Count: {out} (should be 0 or only active generations)")

    print("\n=== Recent videos on server (last 5) ===")
    out, _ = run_cmd(ssh, "ls -t /var/www/html/vidgenerator/videos/*.mp4 2>/dev/null | head -5 | xargs -I{} sh -c 'printf \"%s %s: \" \"$(stat -c%s {})\" \"$(basename {})\"; ffprobe -v quiet -show_entries format=duration -of csv=p=0 \"{}\" 2>/dev/null; echo'")
    print(out)

    print("\n=== Checking fix is deployed (grep for size check) ===")
    out, _ = run_cmd(ssh, "grep -n 'getsize.*>= 1024' /var/www/html/vidgenerator/backend/routes/missing_endpoints_routes.py | head -3")
    print(out or "(not found - fix may not be deployed)")

    out, _ = run_cmd(ssh, "grep -n '_cleanup_partial' /var/www/html/vidgenerator/backend/services/video_generator_service.py | head -3")
    print(out or "(not found - fix may not be deployed)")

    ssh.close()

if __name__ == "__main__":
    main()

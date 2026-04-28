"""Check recent video durations on production server."""
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

    print("=== Recent videos on server ===")
    out, _ = run_cmd(ssh, "ls -lat /var/www/html/vidgenerator/videos/*.mp4 2>/dev/null | head -15")
    print(out)

    print("\n=== Durations (recent 8) ===")
    out, _ = run_cmd(ssh, "ls -t /var/www/html/vidgenerator/videos/*.mp4 2>/dev/null | head -8 | xargs -I{} sh -c 'printf \"{}: \"; ffprobe -v quiet -show_entries format=duration -of csv=p=0 \"{}\" 2>/dev/null; echo'")
    print(out)

    print("\n=== Server MoviePy version ===")
    out, err = run_cmd(ssh, "python3 -c 'import moviepy; print(moviepy.__version__)' 2>&1")
    print(out or err)

    print("\n=== ffmpeg version ===")
    out, _ = run_cmd(ssh, "ffmpeg -version 2>&1 | head -1")
    print(out)

    ssh.close()

if __name__ == "__main__":
    main()

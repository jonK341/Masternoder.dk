"""Check uWSGI config, nohup.out errors, and generate a test video on server."""
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

    print("=== uwsgi.ini ===")
    out, _ = run_cmd(ssh, "cat /var/www/html/vidgenerator/uwsgi.ini 2>/dev/null")
    print(out or "(not found)")

    print("\n=== nohup.out (last 40 lines) ===")
    out, _ = run_cmd(ssh, "tail -40 /var/www/html/vidgenerator/nohup.out 2>/dev/null")
    print(out or "(not found)")

    print("\n=== Error log (last 30 lines) ===")
    out, _ = run_cmd(ssh, "tail -30 /var/www/html/vidgenerator/logs/errors/ 2>/dev/null || tail -30 /var/log/uwsgi/app/vidgenerator.log 2>/dev/null || echo 'no error log'")
    print(out)

    print("\n=== Current uWSGI worker Python ===")
    out, _ = run_cmd(ssh, "ls -la /proc/$(pgrep -f uwsgi | head -1)/exe 2>/dev/null")
    print(out or "(no uwsgi process)")

    print("\n=== Memory info ===")
    out, _ = run_cmd(ssh, "free -m")
    print(out)

    print("\n=== Test: can venv generate a short video? ===")
    test_script = """
import sys
sys.path.insert(0, '/var/www/html/vidgenerator')
from backend.services.video_generator_service import generate_rich_video_sync
segs = [
    {'title': 'Test', 'description': 'A test segment for video generation.', 'duration': 3},
]
path, err = generate_rich_video_sync('server-test-video', segs, width=320, height=240, add_audio=False)
if err:
    print('ERROR:', err)
elif path:
    import os
    print('SUCCESS. Size:', os.path.getsize(path), 'bytes')
else:
    print('FAILED: no path, no error')
"""
    out, err = run_cmd(ssh, f"cd /var/www/html/vidgenerator && /var/www/html/vidgenerator/.venv/bin/python -c \"{test_script.replace(chr(10), ';').replace('\"','\\\"')}\" 2>&1", timeout=120)
    print(out or err or "(no output)")

    ssh.close()

if __name__ == "__main__":
    main()

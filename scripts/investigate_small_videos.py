"""Investigate what the small/failed video files contain."""
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

    # Check contents of a 48-byte file
    print("=== Contents of 48-byte video files ===")
    files_48 = [
        "91741161-1344-41ec-be4b-cc0807da9047",
        "770e37d6-1a37-43df-b181-3d1eaa9c4736",
        "46fa1903-5238-4b0f-a594-986dd10f2d5a",
    ]
    for fid in files_48:
        out, _ = run_cmd(ssh, f"xxd /var/www/html/vidgenerator/videos/{fid}.mp4 2>/dev/null | head -4")
        print(f"\n{fid}.mp4 (hex):")
        print(out or "(empty)")
        out, _ = run_cmd(ssh, f"cat /var/www/html/vidgenerator/videos/{fid}.mp4 2>/dev/null")
        print(f"Text content: {repr(out)}")

    # Check if there are .status.json or pipeline files for these
    print("\n=== Status/pipeline files for failed videos ===")
    for fid in files_48:
        out, _ = run_cmd(ssh, f"ls -la /var/www/html/vidgenerator/videos/{fid}* 2>/dev/null")
        print(f"\n{fid}:")
        print(out or "(not found)")
        out, _ = run_cmd(ssh, f"cat /var/www/html/vidgenerator/videos/{fid}.status.json 2>/dev/null")
        if out:
            print(f"  Status: {out}")

    # Check uwsgi.log around the time of failures (11:28-11:43)
    print("\n=== uWSGI log at time of failures ===")
    out, _ = run_cmd(ssh, "grep -A2 -B2 '11:2[0-9]\\|11:3[0-9]\\|11:4[0-9]' /var/www/html/vidgenerator/uwsgi.log 2>/dev/null | grep -E 'error|fail|video|generat|ERROR|WARN|killed|harakiri' -i | head -30")
    print(out or "(nothing)")

    # Check harakiri (timeout kill) events
    print("\n=== Harakiri events (worker timeout kills) ===")
    out, _ = run_cmd(ssh, "grep -i harakiri /var/www/html/vidgenerator/uwsgi.log 2>/dev/null | tail -20")
    print(out or "(none)")

    # Check OOM events
    print("\n=== OOM killer events today ===")
    out, _ = run_cmd(ssh, "dmesg 2>/dev/null | grep -i 'oom\\|killed process\\|out of memory' | tail -15")
    print(out or "(none)")

    ssh.close()

if __name__ == "__main__":
    main()

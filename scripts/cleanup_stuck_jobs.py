"""Fix stuck 'processing' jobs on production server (run this locally, it SSH's to server)."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()

    # Upload a cleanup script to the server
    cleanup_code = '''import json, os, glob
from datetime import datetime, timezone

videos_dir = "/var/www/html/vidgenerator/videos"
updated = 0
for sf in glob.glob(os.path.join(videos_dir, "*.status.json")):
    try:
        with open(sf) as f:
            data = json.load(f)
        if data.get("status") == "processing":
            doc_id = data.get("id", "")
            mp4 = os.path.join(videos_dir, doc_id + ".mp4")
            valid = os.path.isfile(mp4) and os.path.getsize(mp4) >= 1024
            if not valid:
                data["status"] = "failed"
                data["message"] = "Encoding interrupted (server restart). Please generate again."
                data["error_message"] = data["message"]
                data["progress"] = 0
                data["updated_at"] = datetime.utcnow().isoformat()
                with open(sf, "w") as f:
                    json.dump(data, f, indent=2)
                updated += 1
                print("Fixed:", os.path.basename(sf))
                # Delete the partial/missing mp4 if it exists but is invalid
                if os.path.isfile(mp4) and os.path.getsize(mp4) < 1024:
                    os.remove(mp4)
                    print("  Deleted partial:", os.path.basename(mp4))
    except Exception as e:
        print("Error", os.path.basename(sf), str(e))
print("Updated", updated, "stuck jobs.")
'''
    tmp_path = '/tmp/cleanup_stuck_jobs.py'
    with sftp.open(tmp_path, 'w') as f:
        f.write(cleanup_code)

    print("=== Fixing stuck processing jobs ===")
    out, err = run_cmd(ssh, f"python3 {tmp_path} 2>&1", timeout=30)
    print(out or err or "(no output)")

    print("\n=== Restarting uWSGI ===")
    out, err = run_cmd(ssh, "systemctl restart uwsgi-vidgenerator 2>&1")
    print(out or err or "ok")

    import time
    time.sleep(3)

    out, err = run_cmd(ssh, "systemctl is-active uwsgi-vidgenerator 2>&1")
    print("uWSGI status:", out)

    print("\n=== Verify: No more bad videos ===")
    out, _ = run_cmd(ssh, "find /var/www/html/vidgenerator/videos -name '*.mp4' -size -1024c 2>/dev/null | wc -l")
    print(f"Small video files remaining: {out}")

    sftp.close()
    ssh.close()

if __name__ == "__main__":
    main()

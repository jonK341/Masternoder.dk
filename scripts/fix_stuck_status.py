"""Fix remaining stuck 'processing' status files on server."""
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
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()

    cleanup_code = '''import json, os, glob
from datetime import datetime

videos_dir = "/var/www/html/vidgenerator/videos"
updated = 0
stuck = glob.glob(os.path.join(videos_dir, "*.status.json"))
for sf in stuck:
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
                with open(sf, "w") as fw:
                    json.dump(data, fw, indent=2)
                updated += 1
                print("Fixed:", os.path.basename(sf))
    except Exception as e:
        print("Error", sf, str(e))
print("Total fixed:", updated)
'''
    with sftp.open('/tmp/fix_stuck.py', 'w') as f:
        f.write(cleanup_code)

    out, err = run_cmd(ssh, "python3 /tmp/fix_stuck.py 2>&1")
    print(out or err)

    # Verify
    out, _ = run_cmd(ssh, "grep -l '\"status\": \"processing\"' /var/www/html/vidgenerator/videos/*.status.json 2>/dev/null | wc -l")
    print(f"Remaining stuck jobs: {out}")

    sftp.close()
    ssh.close()

if __name__ == "__main__":
    main()

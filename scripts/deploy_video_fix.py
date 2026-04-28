"""Deploy video fix: upload changed files and clean up bad videos on server."""
import paramiko
import os
import scp as scp_module

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run_cmd(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def upload_file(sftp, local_path, remote_path):
    sftp.put(local_path, remote_path)
    print(f"  Uploaded: {os.path.basename(local_path)} -> {remote_path}")

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()

    print("=== Uploading fixed files ===")
    upload_file(
        sftp,
        os.path.join(BASE_LOCAL, 'backend', 'services', 'video_generator_service.py'),
        f"{BASE_REMOTE}/backend/services/video_generator_service.py"
    )
    upload_file(
        sftp,
        os.path.join(BASE_LOCAL, 'backend', 'routes', 'missing_endpoints_routes.py'),
        f"{BASE_REMOTE}/backend/routes/missing_endpoints_routes.py"
    )

    print("\n=== Cleaning up bad video files (< 1024 bytes) ===")
    out, _ = run_cmd(ssh, f"find {BASE_REMOTE}/videos -name '*.mp4' -size -1024c -ls 2>/dev/null")
    print("Files to delete:")
    print(out or "(none)")

    out, _ = run_cmd(ssh, f"find {BASE_REMOTE}/videos -name '*.mp4' -size -1024c -delete -print 2>/dev/null")
    print("Deleted:", out or "(none)")

    print("\n=== Updating stuck 'processing' status files ===")
    cleanup_script = """
import json, os, glob
from datetime import datetime, timezone

videos_dir = '/var/www/html/vidgenerator/videos'
updated = 0
for sf in glob.glob(os.path.join(videos_dir, '*.status.json')):
    try:
        with open(sf) as f:
            data = json.load(f)
        if data.get('status') == 'processing':
            doc_id = data.get('id', '')
            mp4 = os.path.join(videos_dir, f'{doc_id}.mp4')
            valid = os.path.isfile(mp4) and os.path.getsize(mp4) >= 1024
            if not valid:
                data['status'] = 'failed'
                data['message'] = 'Video encoding was interrupted (server restart). Please generate again.'
                data['error_message'] = data['message']
                data['progress'] = 0
                data['updated_at'] = datetime.utcnow().isoformat()
                with open(sf, 'w') as f:
                    json.dump(data, f, indent=2)
                updated += 1
                print(f'  Fixed: {os.path.basename(sf)}')
    except Exception as e:
        print(f'  Error {os.path.basename(sf)}: {e}')
print(f'Updated {updated} stuck jobs.')
"""
    out, err = run_cmd(ssh, f"python3 -c \"{cleanup_script.replace(chr(10), ';').replace('\"', chr(39))}\" 2>&1", timeout=30)
    print(out or err or "(no output)")

    print("\n=== Reloading uWSGI ===")
    out, err = run_cmd(ssh, "systemctl reload uwsgi-vidgenerator 2>&1 || uwsgi --reload /tmp/uwsgi.pid 2>&1 || touch /var/www/html/vidgenerator/uwsgi.reload 2>&1")
    print(out or err or "ok")
    
    out, err = run_cmd(ssh, "systemctl status uwsgi-vidgenerator 2>/dev/null | head -5")
    print(out)

    sftp.close()
    ssh.close()
    print("\n=== Done ===")

if __name__ == "__main__":
    main()

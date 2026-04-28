"""Deploy points userId fix - replaces hardcoded 'default_user' in JS files."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_REMOTE = "/var/www/html/vidgenerator"

JS_FILES = [
    "vidgenerator/static/js/points-page.js",
    "vidgenerator/static/js/all-api-integration.js",
    "vidgenerator/static/js/point-analytics-dashboard.js",
    "vidgenerator/static/js/universal-auto-save-status.js",
    "vidgenerator/static/js/comprehensive-api-integration.js",
]

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()

    print("=== Uploading points userId fix JS files ===")
    for rel_path in JS_FILES:
        local = os.path.join(BASE_LOCAL, rel_path)
        remote = f"{BASE_REMOTE}/{rel_path[len('vidgenerator/'):]}"
        sftp.put(local, remote)
        print(f"  Uploaded: {os.path.basename(local)}")

    sftp.close()
    ssh.close()
    print("\nDone. No server restart needed (static JS files).")

if __name__ == "__main__":
    main()

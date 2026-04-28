"""Deploy the final on_progress fix to production server."""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run_cmd(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()

    print("=== Uploading final fixed service file ===")
    sftp.put(
        os.path.join(BASE_LOCAL, 'backend', 'services', 'video_generator_service.py'),
        f"{BASE_REMOTE}/backend/services/video_generator_service.py"
    )
    print("  Uploaded video_generator_service.py")

    print("\n=== Restarting uWSGI gracefully ===")
    try:
        # Use a short timeout - restart will kill the connection
        ssh.exec_command("systemctl restart uwsgi-vidgenerator", timeout=5)
    except Exception:
        pass  # Expected - restart kills connection

    sftp.close()
    ssh.close()
    
    print("  Restart command sent (connection drop is expected)")
    time.sleep(5)

    # Verify with a new connection
    ssh2 = paramiko.SSHClient()
    ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh2.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    out, _ = run_cmd(ssh2, "systemctl is-active uwsgi-vidgenerator 2>/dev/null")
    print(f"  uWSGI status: {out}")

    print("\n=== Verifying fixes on server ===")
    out, _ = run_cmd(ssh2, "grep -c '_cleanup_partial\\|getsize.*>= 1024\\|_is_final\\|_sidecar_status' /var/www/html/vidgenerator/backend/services/video_generator_service.py 2>/dev/null")
    print(f"  Fix lines found in service: {out}")

    out, _ = run_cmd(ssh2, "find /var/www/html/vidgenerator/videos -name '*.mp4' -size -1024c 2>/dev/null | wc -l")
    print(f"  Small/bad video files: {out} (should be 0)")

    out, _ = run_cmd(ssh2, "grep -l '\"status\": \"processing\"' /var/www/html/vidgenerator/videos/*.status.json 2>/dev/null | wc -l")
    print(f"  Stuck processing jobs: {out} (should be 0)")

    ssh2.close()
    print("\n=== All done! ===")

if __name__ == "__main__":
    main()

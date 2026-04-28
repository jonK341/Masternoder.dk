"""Check the completed video on production."""
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
    
    vid_id = "117f2ac1-8bdf-4589-a565-e967bbe5b686"
    base = f"/var/www/html/vidgenerator/videos/{vid_id}"
    
    print(f"[1] Video file...")
    out, _ = run_cmd(ssh, f"ls -la {base}.mp4")
    print(f"  {out}")
    
    print(f"\n[2] Status sidecar...")
    out, _ = run_cmd(ssh, f"cat {base}.status.json 2>/dev/null")
    print(f"  {out[:400]}")
    
    print(f"\n[3] Pipeline file...")
    out, _ = run_cmd(ssh, f"cat {base}.pipeline.json 2>/dev/null")
    print(f"  {out[:800]}")
    
    print(f"\n[4] Probe video with ffprobe...")
    out, _ = run_cmd(ssh, f"ffprobe -v quiet -print_format json -show_format -show_streams {base}.mp4 2>/dev/null | head -40")
    print(f"  {out[:600]}")
    
    ssh.close()

if __name__ == "__main__":
    main()

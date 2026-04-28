"""Check content of newly generated video."""
import paramiko
import os
import json

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
    
    vid_id = "ca9c263a-eed0-441c-a789-a8763d044498"
    base = f"/var/www/html/vidgenerator/videos/{vid_id}"
    
    print(f"Video: {vid_id}")
    print("=" * 60)
    
    out, _ = run_cmd(ssh, f"ls -la {base}.mp4")
    print(f"File: {out}")
    
    print(f"\nPipeline segments:")
    out, _ = run_cmd(ssh, f"cat {base}.pipeline.json 2>/dev/null")
    if out:
        data = json.loads(out)
        segs = data.get("rearranged_segments", [])
        print(f"  Title: {data.get('title')}")
        print(f"  Prompt: {data.get('prompt')[:80]}")
        print(f"  Segments: {len(segs)}")
        total_dur = 0
        for s in segs:
            dur = s.get("duration", 0)
            total_dur += dur
            print(f"    [{dur}s] {s.get('title')}: {s.get('description', '')[:70]}")
        print(f"  Total duration: {total_dur}s")
    
    print(f"\nffprobe:")
    out, _ = run_cmd(ssh, f"ffprobe -v quiet -print_format json -show_format {base}.mp4 2>/dev/null")
    if out:
        fmt = json.loads(out).get("format", {})
        print(f"  Duration: {fmt.get('duration')}s")
        print(f"  Size: {fmt.get('size')} bytes")
        print(f"  Bitrate: {fmt.get('bit_rate')} bps")
    
    ssh.close()

if __name__ == "__main__":
    main()

"""Check AI pipeline data on latest video."""
import paramiko, os, json

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
    
    vid_id = "8e428770-2532-447c-81e8-393a70030d45"
    base = f"/var/www/html/vidgenerator/videos/{vid_id}"
    
    stdin, stdout, stderr = ssh.exec_command(f"ls -la {base}.mp4")
    print(f"File: {stdout.read().decode().strip()}")
    
    stdin, stdout, stderr = ssh.exec_command(f"cat {base}.pipeline.json 2>/dev/null")
    out = stdout.read().decode().strip()
    if out:
        data = json.loads(out)
        segs = data.get("rearranged_segments", [])
        print(f"\nTitle: {data.get('title')}")
        print(f"Segments: {len(segs)}\n")
        for i, s in enumerate(segs):
            print(f"  Segment {i+1}:")
            print(f"    Title:       {s.get('title')}")
            print(f"    Description: {s.get('description', '')[:100]}")
            print(f"    Duration:    {s.get('duration')}s")
            print(f"    Mood:        {s.get('mood', '(none)')}")
            print(f"    Tagline:     {s.get('tagline', '(none)')}")
            print(f"    BG Color:    {s.get('bg_color', '(default)')}")
            print()
    
    stdin, stdout, stderr = ssh.exec_command(f"ffprobe -v quiet -print_format json -show_format {base}.mp4 2>/dev/null")
    out = stdout.read().decode().strip()
    if out:
        fmt = json.loads(out).get("format", {})
        print(f"Video: {fmt.get('duration')}s, {fmt.get('size')} bytes")
    
    ssh.close()

if __name__ == "__main__":
    main()

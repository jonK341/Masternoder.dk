"""Inspect the remaining stuck status files."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    out, _ = run_cmd(ssh, """
files=$(grep -l '"status": "processing"' /var/www/html/vidgenerator/videos/*.status.json 2>/dev/null)
for f in $files; do
    echo "=== $f ==="
    cat "$f"
    echo ""
    id=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('id',''))" 2>/dev/null)
    if [ -n "$id" ]; then
        mp4="/var/www/html/vidgenerator/videos/${id}.mp4"
        if [ -f "$mp4" ]; then
            sz=$(stat -c%s "$mp4")
            echo "MP4 size: $sz bytes"
            ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$mp4" 2>/dev/null || echo "ffprobe: N/A"
        else
            echo "MP4: not found"
        fi
    fi
    echo "---"
done
""")
    print(out)
    ssh.close()

if __name__ == "__main__":
    main()

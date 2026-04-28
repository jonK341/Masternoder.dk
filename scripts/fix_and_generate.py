"""Fix dirs, restart, and generate a test video."""
import paramiko
import requests
import time
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

print("1. Creating necessary directories...")
cmds = [
    "mkdir -p /var/www/html/logs/video_status",
    "mkdir -p /var/www/html/logs/unified_points",
    "chown -R www-data:www-data /var/www/html/logs",
    "chmod -R 775 /var/www/html/logs",
    "mkdir -p /var/www/html/vidgenerator/output",
    "chown -R www-data:www-data /var/www/html/vidgenerator/output",
]
for cmd in cmds:
    ssh.exec_command(cmd)
    time.sleep(0.2)
print("   Done")

print("\n2. Restarting uWSGI...")
ssh.exec_command("service uwsgi restart")
time.sleep(4)
stdin, stdout, stderr = ssh.exec_command("ps aux | grep uwsgi | grep -v grep | wc -l")
count = stdout.read().decode().strip()
print(f"   uWSGI workers: {count}")

ssh.close()

print("\n3. Starting video generation...")
BASE = "https://masternoder.dk/vidgenerator"
payload = {
    "prompt": "The rise of artificial intelligence: from Turing to deep learning breakthroughs",
    "title": "The AI Revolution",
    "duration": 30,
    "content_category": "science",
    "resolution": "1280x720",
    "use_context": True,
}

r = requests.post(f"{BASE}/api/unified/generate-video", json=payload, timeout=30)
data = r.json()
vid_id = data.get("video_id")
print(f"   Video ID: {vid_id}")

if not vid_id:
    print(f"   Error: {json.dumps(data, indent=2)}")
    exit()

print("\n4. Polling progress...")
last_pct = -1
for i in range(120):
    time.sleep(3)
    try:
        r = requests.get(f"{BASE}/api/documentary/progress/{vid_id}", timeout=15)
        st = r.json()
        pct = st.get("progress", 0)
        msg = st.get("message", "")
        status = st.get("status", "")

        if pct != last_pct or i % 10 == 0:
            print(f"   [{pct:3d}%] {status}: {msg}")
            last_pct = pct

        if status in ("completed", "complete", "done"):
            url = st.get("video_url")
            print(f"\n   COMPLETE!")
            if url:
                full = url if url.startswith("http") else f"https://masternoder.dk{url}"
                print(f"   URL: {full}")
            break

        if status in ("failed", "error"):
            err = st.get("error") or st.get("error_message", "unknown")
            print(f"\n   FAILED: {err}")
            break
    except Exception as e:
        if i % 5 == 0:
            print(f"   poll error: {e}")

import os
print("\nDone.")

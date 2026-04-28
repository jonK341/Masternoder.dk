"""Read the pipeline JSON for the latest video with images."""
import paramiko
import json

VID_ID = "de484c8f-588e-465a-9e8e-126994cba16c"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password='eD)2[K+[S#m_#$3!', timeout=10)

stdin, stdout, stderr = ssh.exec_command(
    f"cat /var/www/html/vidgenerator/videos/{VID_ID}.pipeline.json"
)
raw = stdout.read().decode()
data = json.loads(raw)

segs = data.get("rearranged_segments") or data.get("segments", [])
img_count = sum(1 for s in segs if s.get("image_path"))
vid_count = sum(1 for s in segs if s.get("ai_video_path"))

print(f"=== Video Pipeline: {VID_ID} ===\n")
print(f"Segments: {len(segs)} | With images: {img_count} | With video clips: {vid_count}\n")

for i, s in enumerate(segs):
    title = (s.get("title") or "?")[:30]
    mood = s.get("mood", "-")
    tag = (s.get("tagline") or "-")[:30]
    img = s.get("image_path", "")
    vid = s.get("ai_video_path", "")
    has_img = "IMG" if img else " - "
    has_vid = "VID" if vid else " - "
    desc = (s.get("description") or "")[:50]
    dur = s.get("duration", "?")
    print(f"  [{i+1:2d}] {title:30s} | {mood:12s} | {has_img} {has_vid} | {dur}s | {tag}")
    if img:
        print(f"       image: {img}")
    if vid:
        print(f"       video: {vid}")

# Check video file size
stdin, stdout, stderr = ssh.exec_command(
    f"ls -lh /var/www/html/vidgenerator/videos/{VID_ID}.mp4"
)
print(f"\nVideo file: {stdout.read().decode().strip()}")

# Count stability images
stdin, stdout, stderr = ssh.exec_command(
    "find /var/www/html/vidgenerator/videos/ -name 'stability_*' -mmin -10 | wc -l"
)
print(f"Stability images generated: {stdout.read().decode().strip()}")

ssh.close()

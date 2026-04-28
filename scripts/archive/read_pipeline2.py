"""Read the pipeline JSON for the latest video."""
import paramiko
import json

VID_ID = "b9dd69d2-6368-4283-bb07-df117ed53996"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password='eD)2[K+[S#m_#$3!', timeout=10)

# Pipeline
stdin, stdout, stderr = ssh.exec_command(
    f"cat /var/www/html/vidgenerator/videos/{VID_ID}.pipeline.json"
)
data = json.loads(stdout.read().decode())

print("=== Pipeline Summary ===\n")
segs = data.get("rearranged_segments") or data.get("segments", [])
print(f"Segments: {len(segs)}\n")
for i, s in enumerate(segs):
    title = (s.get("title") or "?")[:30]
    mood = s.get("mood", "-")
    tagline = (s.get("tagline") or "-")[:35]
    img = s.get("image_path", "-")
    vid = s.get("ai_video_path", "-")
    dur = s.get("duration", "?")
    has_img = "IMG" if img and img != "-" else " - "
    has_vid = "VID" if vid and vid != "-" else " - "
    print(f"  [{i+1:2d}] {title:30s} | mood={mood:12s} | {has_img} {has_vid} | {dur}s")
    if img and img != "-":
        print(f"       image: {img}")

# Check for stability images
stdin, stdout, stderr = ssh.exec_command(
    "find /var/www/html/vidgenerator/videos/ -name 'stability_*' -mmin -10 2>/dev/null"
)
imgs = stdout.read().decode().strip()
print(f"\nStability images found:")
if imgs:
    for line in imgs.split("\n"):
        print(f"  {line}")
else:
    print("  None")

# Video file size
stdin, stdout, stderr = ssh.exec_command(
    f"ls -lh /var/www/html/vidgenerator/videos/{VID_ID}.mp4 2>/dev/null"
)
print(f"\nVideo: {stdout.read().decode().strip()}")

ssh.close()

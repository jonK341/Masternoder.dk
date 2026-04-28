"""Read the pipeline JSON for the generated video."""
import paramiko
import json

VID_ID = "f556cf72-e306-4cc0-9ab5-21f0e120bf0e"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

stdin, stdout, stderr = ssh.exec_command(
    f"cat /var/www/html/vidgenerator/videos/{VID_ID}.pipeline.json"
)
data = json.loads(stdout.read().decode())

print("=== Pipeline Summary ===\n")
print(f"Title: {data.get('title')}")
print(f"Method: {data.get('generation_method')}")
print(f"Quality: {data.get('quality_mode')}")

segs = data.get("rearranged_segments") or data.get("segments", [])
print(f"\nSegments: {len(segs)}")
for i, s in enumerate(segs):
    title = (s.get("title") or "?")[:30]
    desc = (s.get("description") or "")[:60]
    mood = s.get("mood", "-")
    tagline = (s.get("tagline") or "-")[:40]
    has_img = "IMG" if s.get("image_path") else "-"
    has_vid = "VID" if s.get("ai_video_path") else "-"
    bg = s.get("bg_color", "-")
    dur = s.get("duration", "?")
    print(f"\n  [{i+1}] {title}")
    print(f"      desc: {desc}...")
    print(f"      mood={mood} | tagline={tagline}")
    print(f"      bg_color={bg} | dur={dur}s | {has_img} {has_vid}")

# Check script text
script = data.get("generated_script", "")
if script:
    print(f"\n=== AI Script (first 500 chars) ===")
    print(script[:500])

# Status file
stdin, stdout, stderr = ssh.exec_command(
    f"cat /var/www/html/vidgenerator/videos/{VID_ID}.status.json"
)
status_data = json.loads(stdout.read().decode())
print(f"\n=== Status ===")
print(json.dumps(status_data, indent=2)[:500])

import os
ssh.close()

"""Generate a conspiracy-themed clip to test communication psychology points."""
import requests, time, json

BASE = "https://masternoder.dk/vidgenerator/api"

video_data = {
    "title": "Hidden Truths Behind Ancient Structures",
    "description": "Exploring the unexplained engineering feats of ancient civilizations. "
                   "From the pyramids of Giza to Gobekli Tepe, these structures defy mainstream explanations. "
                   "Were ancient builders guided by advanced knowledge lost to history?",
    "duration": 60,
    "short_clip": True,
    "use_context": True,
    "ai_content": True,
    "quality_mode": "auto",
    "encode_profile": "fast_ai",
    "generation_method": "ai",
    "content_category": "conspiracy",
    "content_context": "alternative history, ancient mysteries, forbidden archaeology",
}

print("=" * 60)
print("GENERATING CONSPIRACY-THEMED CLIP")
print("=" * 60)

r = requests.post(f"{BASE}/generator/create", json=video_data, timeout=30)
print(f"Status: {r.status_code}")
data = r.json()
vid_id = data.get("documentary_id") or data.get("id")
print(f"Video ID: {vid_id}")

if not vid_id:
    print(f"ERROR: {data}")
    exit(1)

for i in range(30):
    time.sleep(3)
    pr = requests.get(f"{BASE}/documentary/progress/{vid_id}", timeout=10)
    pdata = pr.json()
    status = pdata.get("status", "unknown")
    progress = pdata.get("progress", 0)
    msg = pdata.get("message", "")
    print(f"  [{i+1:2d}] {status:14s} {progress:3d}% - {msg}")
    if status in ("completed", "failed"):
        break

if status == "completed":
    print(f"\nDONE! {BASE.replace('/api','')}/api/documentary/video/{vid_id}")

# Check points
print("\n" + "=" * 60)
print("POINTS CHECK")
print("=" * 60)
pr = requests.get(f"{BASE}/points/all?user_id=default_user", timeout=10)
pts = pr.json().get("points", {})
systems = pts.get("systems", {})
print(f"  xp_total:                    {pts.get('xp_total', 0)}")
print(f"  generation_points:           {systems.get('generation_points', 0)}")
print(f"  activity_points:             {systems.get('activity_points', 0)}")
print(f"  knowledge_points:            {systems.get('knowledge_points', 0)}")
print(f"  coins:                       {systems.get('coins', 0)}")
print(f"  communication_psychology_pts: {systems.get('communication_psychology_points', 0)}")
print(f"  level:                       {pts.get('level', 0)}")

"""Generate a video and poll progress."""
import requests
import json
import time

BASE = "https://masternoder.dk/vidgenerator"

payload = {
    "prompt": "The rise of artificial intelligence: from Turing to deep learning",
    "title": "AI Revolution",
    "duration": 30,
    "content_category": "science",
    "resolution": "1280x720",
    "use_context": True,
}

print("Starting video generation...")
r = requests.post(f"{BASE}/api/unified/generate-video", json=payload, timeout=30)
data = r.json()
vid_id = data.get("video_id")
print(f"Video ID: {vid_id}")
if not vid_id:
    print(json.dumps(data, indent=2)[:500])
    exit()

print("Polling...")
last_pct = -1
for i in range(90):
    time.sleep(4)
    try:
        r = requests.get(f"{BASE}/api/documentary/progress/{vid_id}", timeout=15)
        st = r.json()
        pct = st.get("progress", 0)
        status = st.get("status", "?")
        msg = st.get("message", "")

        if pct != last_pct or i % 8 == 0:
            print(f"  [{pct:3d}%] {status}: {msg}")
            last_pct = pct

        if status in ("completed", "complete", "done"):
            url = st.get("video_url", "")
            full = url if url.startswith("http") else f"https://masternoder.dk{url}" if url else "?"
            print(f"\nCOMPLETE! URL: {full}")
            break

        if status in ("failed", "error"):
            err = st.get("error") or st.get("error_message", "unknown")
            print(f"\nFAILED: {err}")
            break
    except Exception as e:
        if i % 5 == 0:
            print(f"  poll error: {e}")

print("Done.")

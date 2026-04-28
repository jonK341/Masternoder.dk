"""Test full AI pipeline: multi-provider LLM + Stability AI images."""
import requests
import time
import json

BASE = "https://masternoder.dk/vidgenerator"

print("=== Testing Full AI Pipeline ===\n")

# 1. Check providers
print("1. Checking AI providers...")
try:
    r = requests.get(f"{BASE}/api/ai/providers", timeout=15)
    if r.status_code == 200:
        data = r.json()
        providers = data if isinstance(data, list) else data.get("providers", [])
        for p in providers:
            status = "READY" if p.get("available") else "OFF"
            print(f"   {p.get('label', p.get('provider'))}: {status}")
except Exception as e:
    print(f"   Error: {e}")

# 2. Generate a video
print("\n2. Starting AI-powered video generation...")
payload = {
    "prompt": "The rise of artificial intelligence: from Alan Turing's vision to modern deep learning breakthroughs. How neural networks learn, the transformer revolution, and what the future holds for humanity.",
    "title": "The AI Revolution: Past, Present & Future",
    "duration": 45,
    "content_category": "science",
    "resolution": "1280x720",
    "use_context": True,
}

try:
    r = requests.post(f"{BASE}/api/unified/generate-video", json=payload, timeout=30)
    data = r.json()
    vid_id = data.get("video_id") or data.get("documentary_id") or data.get("id")
    print(f"   Video ID: {vid_id}")
    print(f"   Status: {data.get('status')}")

    if not vid_id:
        print(f"   Full response: {json.dumps(data, indent=2)[:500]}")
        exit()

    # 3. Poll for completion
    print("\n3. Polling progress...")
    for attempt in range(90):
        time.sleep(5)
        try:
            r = requests.get(f"{BASE}/api/documentary/progress/{vid_id}", timeout=20)
            st = r.json()
            pct = st.get("progress", 0)
            msg = st.get("message", st.get("current_step", ""))
            status = st.get("status", "")
            print(f"   [{pct:3d}%] {status}: {msg}")

            if status in ("completed", "complete", "done"):
                url = st.get("video_url") or st.get("url")
                print(f"\n   COMPLETE!")
                if url:
                    full_url = url if url.startswith("http") else f"https://masternoder.dk{url}"
                    print(f"   Video URL: {full_url}")

                # Check pipeline metadata
                segs = st.get("segments", [])
                if not segs:
                    try:
                        r2 = requests.get(f"{BASE}/api/documentary/pipeline/{vid_id}", timeout=10)
                        if r2.status_code == 200:
                            segs = r2.json().get("segments", [])
                    except Exception:
                        pass

                if segs:
                    print(f"\n   Segments: {len(segs)}")
                    for i, s in enumerate(segs):
                        has_img = "IMG" if s.get("image_path") else "-"
                        has_vid = "VID" if s.get("ai_video_path") else "-"
                        mood = s.get("mood", "-")
                        tag = (s.get("tagline") or "-")[:35]
                        title = (s.get("title") or "?")[:28]
                        print(f"   [{i+1}] {title:28s} | {mood:12s} | {tag:35s} | {has_img} {has_vid}")
                break

            if status in ("failed", "error"):
                err = st.get("error") or st.get("error_message", "unknown")
                print(f"\n   FAILED: {err}")
                break
        except Exception as e:
            print(f"   poll error: {e}")

except Exception as e:
    print(f"   Error: {e}")

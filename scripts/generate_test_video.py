"""Generate a test video via the production API and download it."""
import requests
import time
import os

BASE = "https://masternoder.dk/vidgenerator"

def main():
    print("=== Generate Test Video ===\n")

    # Start generation
    print("1. Starting video generation...")
    r = requests.post(f"{BASE}/api/generator/create", json={
        "title": "AI Technology Documentary",
        "description": "An AI documentary about the rise of machine learning and neural networks that are changing our world.",
        "prompt": "An AI documentary about the rise of machine learning and neural networks that are changing our world.",
        "user_id": "test_user",
        "duration": 30,
        "short_clip": True,
        "generation_method": "adaptive_ai_v2",
        "quality_mode": "auto",
        "encode_profile": "fast_ai",
        "use_context": False,
    }, timeout=15)

    if not r.ok:
        print(f"   Error: HTTP {r.status_code}")
        try: print("  ", r.json())
        except: print("  ", r.text[:200])
        return

    d = r.json()
    if not d.get("success"):
        print(f"   Failed: {d.get('error') or d}")
        return

    doc_id = d.get("documentary_id") or d.get("video_id") or d.get("id")
    print(f"   Started! doc_id = {doc_id}")
    print(f"   Status: {d.get('status')}")

    # Poll progress
    print("\n2. Waiting for generation...")
    attempts = 0
    while attempts < 120:
        time.sleep(3)
        attempts += 1
        try:
            pr = requests.get(f"{BASE}/api/documentary/progress/{doc_id}", timeout=10)
            pd = pr.json()
            progress = pd.get("progress", 0)
            status = pd.get("status", "processing")
            message = pd.get("message", "")
            print(f"   [{progress}%] {status} - {message}")

            if status in ("completed", "done") or progress >= 100:
                print(f"\n   Done! video_url = {pd.get('video_url')}")
                break
            elif status in ("failed", "error"):
                print(f"\n   Failed: {pd.get('error_message') or message}")
                return
        except Exception as e:
            print(f"   Poll error: {e}")
            continue

    # Download the video
    video_url = f"{BASE}/api/documentary/video/{doc_id}"
    print(f"\n3. Downloading video from {video_url} ...")
    try:
        vr = requests.get(video_url, timeout=30, stream=True)
        if vr.ok and "video" in vr.headers.get("content-type", ""):
            out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vidgenerator", "videos", f"{doc_id}.mp4")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "wb") as f:
                for chunk in vr.iter_content(chunk_size=8192):
                    f.write(chunk)
            size = os.path.getsize(out_path)
            print(f"   Saved: {out_path}")
            print(f"   Size: {size:,} bytes")
            if size >= 1024:
                print("\n   SUCCESS - video generated correctly!")
            else:
                print("\n   WARNING - file too small, may be invalid")
        else:
            print(f"   Response: HTTP {vr.status_code}, Content-Type: {vr.headers.get('content-type')}")
            print("  ", vr.text[:200])
    except Exception as e:
        print(f"   Download error: {e}")

if __name__ == "__main__":
    main()

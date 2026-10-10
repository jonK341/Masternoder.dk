#!/usr/bin/env python3
"""
Trigger a clip or video on production (masternoder.dk) to verify the generator.
Usage:
  python scripts/trigger_clip_or_video.py clip     # try AI clip
  python scripts/trigger_clip_or_video.py video   # try full video (short_clip mode)
"""
import os
import sys
import json

try:
    import requests
except ImportError:
    print("Install: pip install requests")
    sys.exit(1)

BASE_URL = os.environ.get("BASE_URL", "https://masternoder.dk").rstrip("/")
if BASE_URL.rstrip("/").endswith("/vidgenerator"):
    BASE_URL = BASE_URL.rstrip("/").rsplit("/vidgenerator", 1)[0]
USER_ID = os.environ.get("USER_ID", "default_user")
TIMEOUT = (10, 90)  # connect, read (video can be slow)


def main():
    mode = (sys.argv[1] or "clip").lower() if len(sys.argv) > 1 else "clip"

    if mode == "clip":
        url = BASE_URL + "/vidgenerator/api/generator/ai-clips"
        if not os.environ.get("TRY_AI_CLIPS_FIRST"):
            url_alt = BASE_URL + "/vidgenerator/api/ai-clips/generate"
            try:
                r = requests.post(
                    url_alt,
                    json={"prompt": "Sunset over the ocean, dramatic light and waves", "user_id": USER_ID, "clip_count": 1},
                    headers={"Content-Type": "application/json"},
                    timeout=TIMEOUT,
                )
                print("POST", url_alt, "->", r.status_code)
                if r.ok:
                    d = r.json()
                    print(json.dumps(d, indent=2)[:800])
                    if d.get("success") and d.get("clips"):
                        print("\n[OK] Clip(s) returned:", len(d["clips"]))
                    return
            except Exception as e:
                print("ai-clips/generate failed:", e)
        payload = {"prompt": "Sunset over the ocean, dramatic light and waves"}
        r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
        print("POST", url, "->", r.status_code)
        try:
            d = r.json()
            print(json.dumps(d, indent=2)[:1200])
            if d.get("success"):
                print("\n[OK] Clip request accepted")
            elif d.get("error") or d.get("message"):
                print("\nResponse:", d.get("error") or d.get("message"))
        except Exception:
            print(r.text[:500])

    elif mode == "video":
        url = BASE_URL + "/vidgenerator/api/generator/create"
        body = {
            "title": "Test video from script",
            "description": "Short test of the AI video generator.",
            "prompt": "Short test of the AI video generator.",
            "theme": "default",
            "user_id": USER_ID,
            "duration": 60,
            "short_clip": True,
            "use_context": True,
            "include_points_in_clip": True,
            "generation_method": "adaptive_ai_v2",
            "quality_mode": "auto",
            "audio_style": "cinematic",
            "template": "ai_content",
            "ai_content": True,
            "encode_profile": "fast_ai",
            "profiling": True,
            "profile_mode": "personalized",
            "content_category": "general",
            "content_context": "Short test",
        }
        r = requests.post(url, json=body, headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
        print("POST", url, "->", r.status_code)
        try:
            d = r.json()
            print(json.dumps(d, indent=2)[:1200])
            doc_id = d.get("documentary_id") or d.get("video_id") or d.get("id")
            if d.get("success") and doc_id:
                print("\n[OK] Video job created. documentary_id:", doc_id)
                print("Poll progress: GET", BASE_URL + "/vidgenerator/api/documentary/progress/" + doc_id)
            elif d.get("error") or d.get("message"):
                print("\nResponse:", d.get("error") or d.get("message"))
        except Exception:
            print(r.text[:500])

    else:
        print("Usage: python scripts/trigger_clip_or_video.py [clip|video]")
        sys.exit(1)


if __name__ == "__main__":
    main()

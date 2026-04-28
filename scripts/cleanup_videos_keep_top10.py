#!/usr/bin/env python3
"""
One-time or cron: keep only the top 10 videos by file size (best quality), delete the rest.
Use after deploying the new retention policy to free server space.
Usage:
  python scripts/cleanup_videos_keep_top10.py
  VIDEOS_DIR=/var/www/html/vidgenerator/videos python scripts/cleanup_videos_keep_top10.py
"""
import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)

os.environ.setdefault("VIDEOS_DIR", os.path.join(_BASE, "vidgenerator", "videos"))

def main():
    from backend.services.video_retention_service import get_all_mp4_with_size, TOP_N, VIDEOS_DIR, _mp4_path, _status_path
    pairs = get_all_mp4_with_size()
    if not pairs:
        print("No videos found in", VIDEOS_DIR)
        return
    keep = {doc_id for doc_id, _ in pairs[:TOP_N]}
    deleted = 0
    for doc_id, size in pairs[TOP_N:]:
        path = _mp4_path(doc_id)
        if os.path.isfile(path):
            try:
                os.remove(path)
                print("Deleted", doc_id, "({} bytes)".format(size))
                deleted += 1
            except Exception as e:
                print("Failed to delete", path, e)
        sp = _status_path(doc_id)
        if os.path.isfile(sp):
            try:
                os.remove(sp)
            except Exception:
                pass
    print("Kept top", TOP_N, "videos. Deleted", deleted, "files.")


if __name__ == "__main__":
    main()

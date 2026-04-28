#!/usr/bin/env python3
"""
Seed one production demo video so the site has at least one vid to show.
Creates vidgenerator/videos/production-demo.mp4 using the same pipeline as the generator.
Run from project root:  python scripts/seed_production_video.py
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)


def main():
    doc_id = "production-demo"
    user_id = "default_user"
    print(f"[Seed] Generating production demo video (id={doc_id})...")

    try:
        from backend.services.generator_context_service import (
            gather_context_for_user,
            context_to_segments,
        )
        from backend.services.video_generator_service import (
            generate_rich_video_sync,
            VIDEOS_DIR,
        )
    except ImportError as e:
        print(f"[Seed] Import error: {e}")
        print("  Run from project root and ensure backend is on PYTHONPATH.")
        return 1

    ctx = gather_context_for_user(user_id)
    segments = context_to_segments(
        ctx,
        user_prompt="Production sample clip – profile, agents, and context.",
        user_title="Production sample clip",
        short=True,
        max_segments=12,
        include_points_in_clip=True,
    )
    if not segments:
        print("[Seed] No segments; using minimal fallback.")
        segments = [
            {"title": "Production sample", "description": "Demo clip.", "duration": 4},
            {"title": "End", "description": "Generated for production.", "duration": 3},
        ]

    def on_progress(percent: int, message: str):
        print(f"  [{percent}%] {message}")

    path, err = generate_rich_video_sync(
        doc_id,
        segments,
        width=1280,
        height=768,
        add_audio=True,
        on_progress=on_progress,
    )
    if err or not path:
        print(f"[Seed] Generation failed: {err or 'unknown'}")
        return 1
    if not os.path.isfile(path):
        print(f"[Seed] File not found after generation: {path}")
        return 1
    print(f"[Seed] Done. Video: {path}")
    print(f"[Seed] Serve at: /vidgenerator/api/documentary/video/{doc_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

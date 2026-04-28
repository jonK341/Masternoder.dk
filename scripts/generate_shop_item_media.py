#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate AI shop hero images (Pollinations via free_image_service) and optional clip jobs.

Writes:
  static/shop/items/<item_id_safe>.jpg
  data/shop_item_media.json  (image_url paths for API merge)

  python scripts/generate_shop_item_media.py --limit 20
  python scripts/generate_shop_item_media.py --dry-run
  python scripts/generate_shop_item_media.py --tag media_priority
  python scripts/generate_shop_item_media.py --clips --base-url http://127.0.0.1:5000
    (requires running app; enqueues POST /api/generator/ai-clips per item)

Run from project root.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _load_items():
    from backend.routes.shop_routes import _get_shop_items

    return _get_shop_items() or []


def _filter_by_tags(items, tag_any):
    """Keep items whose tags intersect tag_any (OR). Empty tag_any = no filter."""
    if not tag_any:
        return items
    want = set(tag_any)
    return [it for it in items if want & set(it.get("tags") or [])]


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate shop item images (AI stills) via Pollinations")
    ap.add_argument("--limit", type=int, default=0, help="Max items to process (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="Print prompts only")
    ap.add_argument("--clips", action="store_true", help="POST ai-clips jobs (needs --base-url)")
    ap.add_argument("--base-url", default=os.environ.get("PLATFORM_BASE_URL", "http://127.0.0.1:5000").rstrip("/"))
    ap.add_argument("--delay", type=float, default=1.5, help="Seconds between image requests")
    ap.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Only items with any of these tags (repeatable; OR). E.g. --tag media_priority",
    )
    args = ap.parse_args()

    os.chdir(_ROOT)
    from backend.services.shop_media_service import (
        build_image_prompt,
        load_manifest,
        manifest_path,
        safe_file_stem,
        save_manifest,
    )
    from backend.services.free_image_service import generate_image

    items = _filter_by_tags(_load_items(), args.tag)
    if args.limit and args.limit > 0:
        items = items[: args.limit]

    static_dir = os.path.join(_ROOT, "static", "shop", "items")
    os.makedirs(static_dir, exist_ok=True)

    manifest = load_manifest()
    done = 0
    errors = []

    for item in items:
        iid = item.get("id")
        if not iid:
            continue
        prompt = build_image_prompt(item)
        fname = safe_file_stem(iid)
        rel_path = f"/static/shop/items/{fname}"
        dest_disk = os.path.join(static_dir, fname)

        if args.dry_run:
            print(f"[dry-run] {iid}: {prompt[:120]}...")
            continue

        print(f"Image: {iid} …")
        r = generate_image(prompt, width=1024, height=576)
        if not r.get("success") or not r.get("local_path"):
            errors.append((iid, r.get("error", "no path")))
            continue
        try:
            shutil.copy2(r["local_path"], dest_disk)
        except Exception as e:
            errors.append((iid, str(e)))
            continue

        manifest[iid] = {
            "image_url": rel_path,
            "poster_url": rel_path,
            "prompt_image": prompt,
            "source": r.get("source", "pollinations"),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        save_manifest(manifest)
        done += 1
        time.sleep(max(0.2, args.delay))

    if args.clips and not args.dry_run:
        try:
            import urllib.request
        except ImportError:
            print("urllib not available")
            return 1
        items_clip = _filter_by_tags(_load_items(), args.tag)
        if args.limit and args.limit > 0:
            items_clip = items_clip[: args.limit]
        for item in items_clip:
            iid = item.get("id")
            if not iid:
                continue
            prompt = (
                f"Short cinematic trailer shot for game shop item: {item.get('name', '')}. "
                f"{(item.get('description') or '')[:200]}"
            )
            body = json.dumps(
                {
                    "prompt": prompt[:1200],
                    "title": f"Shop clip: {item.get('name', iid)[:80]}",
                    "user_id": "shop_media_batch",
                    "clip_count": 1,
                    "duration": 5,
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                f"{args.base_url}/api/generator/ai-clips",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                print(f"  clip job {iid}: {raw[:200]}")
            except Exception as e:
                print(f"  clip job {iid} failed: {e}")
            time.sleep(2.0)

    print()
    print(f"Manifest: {manifest_path()}")
    print(f"Images OK: {done}")
    if errors:
        print(f"Errors: {len(errors)}")
        for iid, err in errors[:10]:
            print(f"  {iid}: {err}")
    return 0 if not errors and (done or args.dry_run) else (1 if errors else 0)


if __name__ == "__main__":
    sys.exit(main())

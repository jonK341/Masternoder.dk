#!/usr/bin/env python3
"""
Smoke-test generation helpers: service check, fresh storyline prep, visual profile.
Run from repo root: python scripts/test_generation_pipeline.py
"""
from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.environ.setdefault("PYTHONPATH", _ROOT + os.pathsep + os.environ.get("PYTHONPATH", ""))


def main() -> int:
    from backend.services.video_generator_service import (
        _check_generation_services,
        _generation_visual_seed,
        _prepare_generation_config,
        _visual_profile_from_seed,
    )

    ok, msg, detail = _check_generation_services()
    print("=== Service check ===")
    print("ok:", ok)
    print("message:", msg or "(none)")
    print(json.dumps(detail, indent=2, default=str))

    cfg = {
        "title": "Pipeline smoke test",
        "prompt": "Urban night markets and the sound of rain on canvas.",
        "generation_method": "adaptive_ai_v2",
        "user_id": "test_user",
    }
    doc_id = "smoke-test-doc-001"
    _prepare_generation_config(doc_id, cfg)
    print("\n=== Fresh config (excerpt) ===")
    print("run_id:", cfg.get("_generation_run_id"))
    print("storyline_addon:", (cfg.get("_storyline_addon") or "")[:400])
    vp = cfg.get("_visual_profile") or _visual_profile_from_seed(_generation_visual_seed(doc_id))
    print("visual_profile:", json.dumps(vp, indent=2, default=str))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

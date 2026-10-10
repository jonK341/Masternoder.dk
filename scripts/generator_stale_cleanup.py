#!/usr/bin/env python3
"""Remove stale generator sidecar/job files (failed or abandoned). Keeps completed MP4s."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

DEFAULT_MAX_AGE_DAYS = 7


def _videos_dir() -> str:
    return os.environ.get("VIDEOS_DIR") or os.path.join(_BASE, "vidgenerator", "videos")


def _mtime_age_days(path: str) -> float:
    try:
        age_sec = time.time() - os.path.getmtime(path)
        return age_sec / 86400.0
    except Exception:
        return 0.0


def _is_failed_sidecar(path: str) -> bool:
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        status = str((data or {}).get("status") or "").lower()
        return status in ("failed", "error")
    except Exception:
        return False


def _reap_stale_encoding_jobs(vdir: str, dry_run: bool = True) -> list:
    """Kill subprocess encodes running longer than duration×3 (E10)."""
    import json
    import signal

    reaped = []
    for name in os.listdir(vdir):
        if not name.endswith(".run.json"):
            continue
        full = os.path.join(vdir, name)
        doc_id = name.replace(".run.json", "")
        try:
            with open(full, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except Exception:
            continue
        pid = int(data.get("pid") or 0)
        dur = max(30, int(data.get("duration_sec") or 180))
        max_sec = dur * 3 + 120
        age_sec = time.time() - os.path.getmtime(full)
        mp4 = os.path.join(vdir, doc_id + ".mp4")
        if os.path.isfile(mp4) and os.path.getsize(mp4) >= 1024:
            if not dry_run:
                try:
                    os.remove(full)
                except Exception:
                    pass
            continue
        if age_sec < max_sec:
            continue
        killed = False
        if pid > 0 and not dry_run:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=10)
                else:
                    os.kill(pid, signal.SIGTERM)
                killed = True
            except Exception:
                pass
        if not dry_run:
            try:
                from backend.services.video_generator_service import _write_status_sidecar, clear_run_sidecar
                _write_status_sidecar(
                    doc_id=doc_id,
                    status="failed",
                    message="Encoding timed out (stale reaper)",
                    error_message=f"Job exceeded {int(max_sec)}s without valid output",
                    progress=0,
                    stage="failed",
                )
                clear_run_sidecar(doc_id)
            except Exception:
                pass
            try:
                os.remove(full)
            except Exception:
                pass
        reaped.append({"doc_id": doc_id, "pid": pid, "age_sec": int(age_sec), "killed": killed})
    return reaped


def run_cleanup(max_age_days: int = DEFAULT_MAX_AGE_DAYS, dry_run: bool = True) -> dict:
    vdir = _videos_dir()
    removed: list[str] = []
    reaped: list[dict] = []
    if not os.path.isdir(vdir):
        return {"success": True, "removed": [], "reaped": [], "videos_dir": vdir, "dry_run": dry_run}

    reaped = _reap_stale_encoding_jobs(vdir, dry_run=dry_run)

    for name in os.listdir(vdir):
        full = os.path.join(vdir, name)
        if not os.path.isfile(full):
            continue
        age = _mtime_age_days(full)
        if age < max_age_days:
            continue

        if name.endswith(".status.json"):
            if _is_failed_sidecar(full) or age >= max_age_days * 2:
                removed.append(full)
        elif name.endswith(".job.json"):
            base = name.replace(".job.json", "")
            mp4 = os.path.join(vdir, base + ".mp4")
            if not os.path.isfile(mp4) or os.path.getsize(mp4) < 1024:
                removed.append(full)

    if not dry_run:
        for p in removed:
            try:
                os.remove(p)
            except Exception:
                pass

    return {
        "success": True,
        "dry_run": dry_run,
        "max_age_days": max_age_days,
        "videos_dir": vdir,
        "removed_count": len(removed),
        "removed": removed[:50],
        "reaped_count": len(reaped),
        "reaped": reaped[:20],
        "at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean stale generator artifacts")
    parser.add_argument("--days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    parser.add_argument("--apply", action="store_true", help="Actually delete files")
    args = parser.parse_args()
    result = run_cleanup(max_age_days=max(1, args.days), dry_run=not args.apply)
    print(f"removed={result['removed_count']} dry_run={result['dry_run']} dir={result['videos_dir']}")
    for p in result.get("removed") or []:
        print(" ", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

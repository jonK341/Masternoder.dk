"""
uWSGI worker pressure index — lightweight saturation signal for throttling.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict


def worker_pressure() -> Dict[str, Any]:
    score = 0.0
    factors: Dict[str, Any] = {}

    # Video queue depth
    try:
        from backend.services.video_job_queue import queue_status

        qs = queue_status()
        qd = int(qs.get("queued") or 0) + int(qs.get("active") or 0)
        factors["video_jobs"] = qd
        score += min(0.4, qd * 0.08)
    except Exception:
        factors["video_jobs"] = 0

    # Casino burst (last minute from sqlite mirror)
    try:
        import sqlite3

        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_dir = os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(root, "logs")
        db_path = os.path.join(log_dir, "casino_ledger.db")
        if os.path.isfile(db_path):
            conn = sqlite3.connect(db_path, timeout=2.0)
            try:
                since = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 60))
                cur = conn.execute(
                    "SELECT COUNT(*) FROM casino_bets WHERE created_at >= ?",
                    (since,),
                )
                burst = int(cur.fetchone()[0] or 0)
                factors["casino_bets_60s"] = burst
                score += min(0.35, burst * 0.02)
            finally:
                conn.close()
    except Exception:
        factors["casino_bets_60s"] = 0

    # Generation health inverse
    try:
        from backend.services.video_generator_service import _check_generation_services

        ok, _, _ = _check_generation_services()
        factors["generation_ready"] = ok
        if not ok:
            score += 0.25
    except Exception:
        factors["generation_ready"] = None

    score = round(min(1.0, max(0.0, score)), 3)
    if score >= 0.8:
        recommendation = "throttle"
    elif score >= 0.5:
        recommendation = "caution"
    else:
        recommendation = "normal"

    return {
        "success": True,
        "score": score,
        "recommendation": recommendation,
        "factors": factors,
    }

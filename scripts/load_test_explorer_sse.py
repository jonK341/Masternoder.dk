#!/usr/bin/env python3
"""Load test explorer SSE stream with concurrent clients (P4 #186).

Usage:
  python scripts/load_test_explorer_sse.py --clients 100 --duration 30
  python scripts/load_test_explorer_sse.py --base-url http://127.0.0.1:5000
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
import sys
import time
import urllib.request


def _sse_worker(base: str, worker_id: int, duration: float) -> dict:
    url = f"{base.rstrip('/')}/api/mn2/explorer/stream"
    events = 0
    errors = 0
    t0 = time.perf_counter()
    end = t0 + duration
    try:
        req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
        with urllib.request.urlopen(req, timeout=duration + 10) as resp:
            while time.perf_counter() < end:
                line = resp.readline()
                if not line:
                    break
                if line.startswith(b"data:"):
                    events += 1
    except Exception:
        errors += 1
    return {
        "worker": worker_id,
        "events": events,
        "errors": errors,
        "duration_s": round(time.perf_counter() - t0, 2),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Explorer SSE load test")
    p.add_argument("--base-url", default=os.environ.get("POST_DEPLOY_BASE_URL", "http://127.0.0.1:5000"))
    p.add_argument("--clients", type=int, default=100)
    p.add_argument("--duration", type=float, default=30.0)
    args = p.parse_args()

    print(f"SSE load test: {args.clients} clients × {args.duration}s @ {args.base_url}")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.clients) as pool:
        futs = [
            pool.submit(_sse_worker, args.base_url, i, args.duration)
            for i in range(args.clients)
        ]
        for fut in concurrent.futures.as_completed(futs):
            results.append(fut.result())

    total_events = sum(r["events"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    print(f"  clients={len(results)} events={total_events} errors={total_errors}")
    if total_errors:
        print(f"  {total_errors} client(s) errored", file=sys.stderr)
        return 1
    print("Load test complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

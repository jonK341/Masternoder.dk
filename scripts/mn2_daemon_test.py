#!/usr/bin/env python3
"""Test masternoder2d RPC daemon health. Usage: python scripts/mn2_daemon_test.py [--extended]"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe MN2 daemon RPC health")
    parser.add_argument("--extended", action="store_true", help="Include wallet + connection info")
    args = parser.parse_args()
    from backend.services.mn2_daemon_health_service import probe_daemon
    result = probe_daemon(extended=args.extended)
    print(json.dumps(result, indent=2))
    return 0 if result.get("healthy") else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verify tab markup in local HTML/CSS before deploy."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("explorer/index.html", [
        r'id="mn2-hub-nav"',
        r"mn2-crypto-hub",
        r'data-mn2-tab="market"',
    ]),
    ("aggregator/index.html", [
        r'id="agg-hub-nav"',
        r"initAggregatorTabs",
        r'class="agg-ideas-section agg-tab-panel" data-agg-tab="ideas"',
    ]),
    ("milkyway/index.html", [
        r'id="milky-hub-nav"',
        r"initMilkywayTabs",
        r'data-milky-tab="tech"',
    ]),
    ("static/css/mn2-crypto-hub.css", [
        r"\.mn2-hub-nav",
        r"\.mn2-tab-panel\[hidden\]",
    ]),
    ("starmap25/index.html", [
        r'id="starmap-hub-nav"',
        r"initStarmapTabs",
        r'data-starmap-tab="monitor"',
    ]),
]


def main() -> int:
    failed = 0
    for rel, patterns in CHECKS:
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        print(f"=== {rel} ===")
        for pattern in patterns:
            if re.search(pattern, text):
                print(f"  OK {pattern}")
            else:
                print(f"  FAIL {pattern}")
                failed += 1
    print("=" * 40)
    if failed:
        print(f"RESULT: {failed} check(s) FAILED")
        return 1
    print("RESULT: all local checks PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

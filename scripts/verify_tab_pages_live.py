#!/usr/bin/env python3
"""Verify deployed tab UI markup and JS on masternoder.dk."""
import re
import sys
import urllib.request

BASE = "https://masternoder.dk"

PAGES = [
    {
        "name": "Profile",
        "path": "/profile",
        "checks": [
            (r'id="profile-hub-nav"', "profile hub nav"),
            (r'data-hub-scroll="wallet"', "wallet tab"),
            (r'data-hub-scroll="skills"', "skills tab"),
            (r'applyFocusedProfileRoute', "tab route JS"),
            (r'data-profile-route="wallet"', "wallet panel route"),
        ],
    },
    {
        "name": "Casino",
        "path": "/casino/",
        "checks": [
            (r'id="casino-games-nav"', "games nav"),
            (r'data-casino-game="crash"', "crash game card"),
            (r'data-casino-game="plinko"', "plinko game card"),
            (r'casino-games-tabbed', "tabbed grid class"),
            (r'casino\.js\?v=20260616', "casino.js cache bust"),
        ],
    },
    {
        "name": "Lab",
        "path": "/lab",
        "checks": [
            (r'id="lab-hub-nav"', "lab hub nav"),
            (r'data-lab-tab="workbench"', "workbench panel"),
            (r'data-lab-tab="chapter"', "chapter panel"),
            (r'initLabTabs', "lab tab init JS"),
        ],
    },
    {
        "name": "Monetization",
        "path": "/monetization",
        "checks": [
            (r'id="mon-hub-nav"', "mon hub nav"),
            (r'data-mon-tab="streams"', "streams panel"),
            (r'data-mon-tab="intelligence"', "intelligence panel"),
            (r'initMonetizationTabs', "mon tab init JS"),
        ],
    },
    {
        "name": "Aggregator",
        "path": "/aggregator",
        "checks": [
            (r'id="agg-hub-nav"', "agg hub nav"),
            (r'agg-tab-panel.*data-agg-tab="ideas"', "ideas panel"),
            (r'initAggregatorTabs', "agg tab init JS"),
            (r'aggregator-monitor\.css\?v=6', "agg css cache bust"),
        ],
    },
    {
        "name": "Milky Way",
        "path": "/milkyway",
        "checks": [
            (r'id="milky-hub-nav"', "milky hub nav"),
            (r'milky-tab-panel.*data-milky-tab="tech"', "tech panel"),
            (r'initMilkywayTabs', "milky tab init JS"),
        ],
    },
    {
        "name": "MN2 Crypto Hub",
        "path": "/explorer",
        "checks": [
            (r'id="mn2-hub-nav"', "mn2 hub nav"),
            (r'mn2-tab-panel.*data-mn2-tab="staking"', "staking panel"),
            (r'mn2-crypto-hub\.js', "hub tab init JS"),
            (r'data-mn2-tab="reserves"', "reserves tab"),
        ],
    },
    {
        "name": "Star Map 25",
        "path": "/starmap25",
        "checks": [
            (r'id="starmap-hub-nav"', "starmap hub nav"),
            (r'starmap-tab-panel.*data-starmap-tab="monitor"', "monitor panel"),
            (r'initStarmapTabs', "starmap tab init JS"),
        ],
    },
    {
        "name": "Staking redirect",
        "path": "/staking-monitor",
        "checks": [
            (r'explorer\?tab=staking', "redirect to hub staking tab"),
        ],
    },
]

JS_CHECKS = [
    ("Casino JS", "/static/js/casino.js", [r"function initCasinoGamesTabs", r"casino-game-tab"]),
]


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "TabSmokeTest/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def main() -> int:
    failed = 0
    print("Live tab UI verification —", BASE, "\n")

    for page in PAGES:
        url = BASE + page["path"]
        print(f"=== {page['name']} ({url}) ===")
        try:
            status, html = fetch(url)
        except Exception as e:
            print(f"  FAIL fetch: {e}")
            failed += 1
            continue
        if status != 200:
            print(f"  FAIL HTTP {status}")
            failed += 1
            continue
        print(f"  OK HTTP 200 ({len(html):,} bytes)")
        for pattern, label in page["checks"]:
            if re.search(pattern, html):
                print(f"  OK {label}")
            else:
                print(f"  FAIL missing {label} ({pattern})")
                failed += 1
        print()

    for label, path, patterns in JS_CHECKS:
        url = BASE + path
        print(f"=== {label} ({url}) ===")
        try:
            status, body = fetch(url)
        except Exception as e:
            print(f"  FAIL fetch: {e}")
            failed += 1
            continue
        if status != 200:
            print(f"  FAIL HTTP {status}")
            failed += 1
            continue
        for pattern in patterns:
            if re.search(pattern, body):
                print(f"  OK {pattern}")
            else:
                print(f"  FAIL missing {pattern}")
                failed += 1
        print()

    print("=" * 40)
    if failed:
        print(f"RESULT: {failed} check(s) FAILED")
        return 1
    print("RESULT: all checks PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

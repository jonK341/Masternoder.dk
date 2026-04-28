#!/usr/bin/env python3
"""
Hard test: verify routes are registered AND URLs respond.
1. Load Flask app and list which front/profile API paths are registered.
2. Run URL timing test (same as test_url_timing.py) against BASE_URL.

Usage:
  python scripts/hard_test_routes_and_urls.py
  python scripts/hard_test_routes_and_urls.py --routes-only   # only check url_map
  python scripts/hard_test_routes_and_urls.py --urls-only     # only run URL timing (no app load)
  BASE_URL=http://127.0.0.1:5002 python scripts/hard_test_routes_and_urls.py
  BASE_URL=https://masternoder.dk python scripts/hard_test_routes_and_urls.py
"""
import argparse
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

os.chdir(BASE)

# Expected path prefixes (from test_url_timing) – must exist in app.url_map
EXPECTED_PREFIXES = [
    "/vidgenerator/api/frontpage/init",
    "/vidgenerator/api/stats/summary",
    "/vidgenerator/api/points/all",
    "/vidgenerator/api/battle/stats",
    "/vidgenerator/api/agent-skillset/all",
    "/vidgenerator/api/aggregator/frontend",
    "/vidgenerator/api/user/bind-session",
    "/vidgenerator/api/user/profile/",
    "/vidgenerator/api/user/identity",
    "/vidgenerator/api/user/account-summary/points",
    "/vidgenerator/api/gallery/recent-temp",
    "/vidgenerator/api/game/hunters/geo-ref",
    "/vidgenerator/api/shop/paypal/control-panel",
    "/vidgenerator/api/agents/activity-feed",
    "/vidgenerator/api/agents/my-agents",
    "/vidgenerator/api/trophies/list",
    "/vidgenerator/api/game/achievements",
    "/vidgenerator/api/battle/pvp/trophies",
]


def run_routes_audit(verbose=True):
    """Load app, check expected paths in url_map, return (missing_list, all_rules)."""
    import sys
    # Suppress blueprint registration prints when we only want route audit
    devnull = open(os.devnull, "w")
    old_stdout, old_stderr = sys.stdout, sys.stderr
    if not verbose:
        sys.stdout = sys.stderr = devnull
    try:
        from src.app import create_app
        app = create_app()
    except Exception as e:
        if not verbose:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            devnull.close()
        raise
    if not verbose:
        sys.stdout, sys.stderr = old_stdout, old_stderr
        devnull.close()

    all_rules = list(app.url_map.iter_rules())

    def rule_matches_prefix(rule, prefix):
        r = rule.rule.rstrip("/")
        p = prefix.rstrip("/")
        return r == p or r.startswith(p + "/")

    missing = []
    matches = {}  # prefix -> list of matching rules
    for p in EXPECTED_PREFIXES:
        matching = [r for r in all_rules if rule_matches_prefix(r, p)]
        if matching:
            matches[p] = matching
        else:
            missing.append(p)
    return missing, matches, all_rules


def main():
    parser = argparse.ArgumentParser(description="Hard test: routes registration + URL timing")
    parser.add_argument("--routes-only", action="store_true", help="Only check registered routes (no URL test)")
    parser.add_argument("--urls-only", action="store_true", help="Only run URL timing test (no app load)")
    parser.add_argument("--quiet", action="store_true", help="Suppress blueprint registration output during route audit")
    args = parser.parse_args()

    do_routes = not args.urls_only
    do_urls = not args.routes_only
    # When running both, default to quiet route audit to avoid duplicate/noisy blueprint output
    quiet_routes = args.quiet or (do_routes and do_urls)

    print("=" * 70)
    print("HARD TEST: Routes registration + URL timing")
    print("=" * 70)

    missing = []
    matches = {}
    if do_routes:
        print("\n[1] Loading Flask app and checking registered routes...")
        try:
            missing, matches, all_rules = run_routes_audit(verbose=not quiet_routes)
        except Exception as e:
            print("  [FAIL] Could not create app:", e)
            import traceback
            traceback.print_exc()
            return 1

        api_count = sum(1 for r in all_rules if "/api" in r.rule)
        print("  Registered API rules (url_map):", api_count)
        print("  Expected path prefixes found:", len(matches), "/", len(EXPECTED_PREFIXES))
        if missing:
            print("  [WARN] Paths NOT in url_map:")
            for m in missing:
                print("    -", m)
        else:
            print("  [OK] All expected path prefixes are registered")
        if matches and (quiet_routes or len(matches) <= 20):
            print("\n  Matching rules (one per expected path):")
            for prefix in EXPECTED_PREFIXES:
                if prefix in matches:
                    r = matches[prefix][0]
                    methods = ",".join(sorted(m for m in (r.methods or set()) if m not in ("HEAD", "OPTIONS")))
                    print("    ", r.rule, " -> ", methods)
    else:
        print("\n[1] Skipped (--urls-only)")

    url_exit = 0
    if do_urls:
        print("\n[2] Running URL timing test (test_url_timing)...")
        import subprocess
        env = os.environ.copy()
        base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5002")
        if base_url == "http://127.0.0.1:5002":
            print("  BASE_URL not set, using http://127.0.0.1:5002 (set BASE_URL for production)")
        env["BASE_URL"] = base_url.rstrip("/")
        # Prevent subprocess from loading Flask app (avoids interleaved blueprint output)
        env["PYTHONPATH"] = ""
        # Production uses 15s read timeout in test_url_timing; allow enough time for 18 requests
        timeout = 400 if "masternoder.dk" in base_url else 120
        try:
            out = subprocess.run(
                [sys.executable, os.path.join(BASE, "scripts", "test_url_timing.py")],
                cwd=BASE,
                env=env,
                capture_output=False,
                timeout=timeout,
            )
            url_exit = out.returncode
        except subprocess.TimeoutExpired:
            print("  [FAIL] URL timing test timed out ({}s)".format(timeout))
            url_exit = 1
        except Exception as e:
            print("  [FAIL] URL timing test error:", e)
            url_exit = 1
    else:
        print("\n[2] Skipped (--routes-only)")

    print("\n" + "=" * 70)
    if do_routes:
        if missing:
            print("  ROUTES: FAIL –", len(missing), "expected path(s) not registered")
        else:
            print("  ROUTES: OK – all expected path prefixes registered")
    if do_urls:
        if url_exit != 0:
            print("  URL TEST: FAIL – some requests failed or timed out (see above)")
        else:
            print("  URL TEST: OK")
    print("=" * 70)
    return 0 if (not missing and (not do_urls or url_exit == 0)) else 1


if __name__ == "__main__":
    sys.exit(main())

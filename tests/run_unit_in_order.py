#!/usr/bin/env python3
"""
Run unit tests in fixed order: 1 Generator, 2 Battle, 3 Trophies, 4 Chat, 5 Gallery, 6 Points, 7 Shop.
Usage: python tests/run_unit_in_order.py [--verbose] [--no-pytest]
  With --no-pytest: discover and run test_*.py under tests/unit/ in order (by name) without pytest.
  Default: run pytest on tests/unit/ (pytest discovers test_01_*.py .. test_07_*.py in order).
"""
import os
import sys
import subprocess

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT.endswith("tests"):
    _PROJECT_ROOT = os.path.dirname(_ROOT)
else:
    _PROJECT_ROOT = _ROOT
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
os.chdir(_PROJECT_ROOT)

# Ordered list of unit test modules (nr 1 .. 10)
UNIT_MODULES = [
    "tests.unit.test_01_generator",
    "tests.unit.test_02_battle",
    "tests.unit.test_03_trophies",
    "tests.unit.test_04_chat",
    "tests.unit.test_05_gallery",
    "tests.unit.test_06_points",
    "tests.unit.test_07_shop",
    "tests.unit.test_08_migrations",
    "tests.unit.test_09_solutions",
    "tests.unit.test_10_content_categories",
]


def run_pytest(verbose=True):
    """Run pytest on tests/unit/; file names sort so test_01 .. test_07 run in order."""
    unit_dir = os.path.join(_PROJECT_ROOT, "tests", "unit")
    cmd = [sys.executable, "-m", "pytest", unit_dir, "-v", "--tb=short"]
    if not verbose:
        cmd.append("-q")
    print("Running:", " ".join(cmd))
    print("Order: test_01_generator .. test_10_content_categories")
    print("=" * 60)
    return subprocess.run(cmd, cwd=_PROJECT_ROOT).returncode


def run_without_pytest(verbose=True):
    """Import each module and run pytest-style test functions (test_*). No pytest required."""
    failed = []
    for mod_name in UNIT_MODULES:
        if verbose:
            print(f"\n--- {mod_name} ---")
        try:
            mod = __import__(mod_name, fromlist=[""])
        except ImportError as e:
            print(f"  SKIP: could not import {mod_name}: {e}")
            failed.append((mod_name, str(e)))
            continue
        for name in dir(mod):
            if name.startswith("test_") and callable(getattr(mod, name)):
                try:
                    getattr(mod, name)()
                    if verbose:
                        print(f"  OK   {name}")
                except Exception as e:
                    if verbose:
                        print(f"  FAIL {name}: {e}")
                    failed.append((f"{mod_name}.{name}", str(e)))
    if failed:
        print("\nFailed:", failed)
        return 1
    print("\nAll unit tests passed.")
    return 0


def main():
    import argparse
    p = argparse.ArgumentParser(description="Run unit tests in order 1..10")
    p.add_argument("--no-pytest", action="store_true", help="Run without pytest (plain Python)")
    p.add_argument("-q", "--quiet", action="store_true", help="Less output")
    args = p.parse_args()
    if args.no_pytest:
        return run_without_pytest(verbose=not args.quiet)
    return run_pytest(verbose=not args.quiet)


if __name__ == "__main__":
    sys.exit(main())

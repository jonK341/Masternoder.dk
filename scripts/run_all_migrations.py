#!/usr/bin/env python3
"""
Run all feature migrations in standalone mode (no Flask).
Use from project root: python scripts/run_all_migrations.py
"""
import os
import sys
import subprocess

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_root)
if sys.path[0] != _root:
    sys.path.insert(0, _root)

MIGRATIONS = [
    ("Battle", "scripts/battle_migration.py"),
    ("Trophies", "scripts/trophies_migration.py"),
    ("Shop", "scripts/shop_purchase_migration.py"),
    ("Chat", "scripts/chat_migration.py"),
    ("Gallery", "scripts/gallery_migration.py"),
    ("Points", "scripts/points_migration.py"),
    ("Generator", "scripts/generator_migration.py"),
]


def main():
    print("=" * 60)
    print("RUNNING ALL MIGRATIONS (--standalone)")
    print("=" * 60)
    results = []
    for name, path in MIGRATIONS:
        script_path = os.path.join(_root, path.replace("/", os.sep))
        if not os.path.isfile(script_path):
            print(f"[SKIP] {name}: {path} not found")
            results.append((name, "skipped", "file not found"))
            continue
        print(f"\n--- {name} ---")
        try:
            out = subprocess.run(
                [sys.executable, script_path, "--standalone"],
                cwd=_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            print(out.stdout or "(no output)")
            if out.stderr:
                print(out.stderr, file=sys.stderr)
            results.append((name, "ok" if out.returncode == 0 else "fail", out.returncode))
        except subprocess.TimeoutExpired:
            print("TIMEOUT")
            results.append((name, "timeout", None))
        except Exception as e:
            print(f"ERROR: {e}")
            results.append((name, "error", str(e)))
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, status, detail in results:
        print(f"  {name}: {status}" + (f" ({detail})" if detail else ""))
    failed = [n for n, s, _ in results if s not in ("ok", "skipped")]
    if failed:
        sys.exit(1)
    print("\nAll migrations completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)

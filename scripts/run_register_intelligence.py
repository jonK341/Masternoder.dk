#!/usr/bin/env python3
"""
Run Register Intelligence - automatic route/blueprint discovery and 404 resolution.
Safe: uses dry-run by default. Use --apply to modify files.
"""
import os
import sys
import json
import argparse

# Ensure project root on path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def main():
    parser = argparse.ArgumentParser(description="Register Intelligence - auto-discover and fix routes")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument("--discover-only", action="store_true", help="Only run discovery, no registration")
    parser.add_argument("--show-404-patterns", action="store_true", dest="show_404", help="Show 404 patterns from logs")
    parser.add_argument("--json", action="store_true", help="Output full report as JSON")
    parser.add_argument("--project-root", default=_project_root, help="Project root path")
    args = parser.parse_args()

    dry_run = not args.apply

    from backend.services.register_intelligence import (
        RegisterIntelligence,
        run_register_intelligence,
        MissingRouteResolver,
    )

    ri = RegisterIntelligence(project_root=args.project_root, dry_run=dry_run)

    # Always run discovery/audit
    report = ri.run_full_audit()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return
    d = report.get("audit", {}).get("summary", {})
    print("=" * 60)
    print("REGISTER INTELLIGENCE AUDIT")
    print("=" * 60)
    print("  Blueprints discovered:", d.get("blueprints", 0))
    print("  Backend routes:", d.get("backend_routes", 0))
    print("  Frontend API calls:", d.get("frontend_apis", 0))
    print("  Potential missing (frontend calls backend lacks):", d.get("potential_missing", 0))
    print("  Mode:", "DRY-RUN" if dry_run else "APPLY")
    print("=" * 60)
    disc = report.get("discovery", {})
    if disc.get("potential_missing"):
        print("\nTop potential missing paths:")
        for p in list(disc["potential_missing"])[:15]:
            print("  -", p)

    if getattr(args, "show_404", False):
        resolver = MissingRouteResolver(project_root=args.project_root)
        patterns = resolver.get_404_patterns()
        print("\n404 Patterns (from log):")
        for norm, data in sorted(patterns.items(), key=lambda x: -x[1].get("count", 0))[:20]:
            print("  %s: count=%d methods=%s" % (norm, data.get("count", 0), data.get("methods", [])))


if __name__ == "__main__":
    main()

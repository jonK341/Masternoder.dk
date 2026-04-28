#!/usr/bin/env python3
"""
Deploy only the files that were changed for the "generator move to root" edit.
Use this instead of deploy_all_and_restart_uwsgi.py when you only want to push
the root-first changes (backend routes, app static_folder, vidgenerator HTML/JS paths,
scripts, docs) and then restart uwsgi.

Usage:
  python scripts/deploy_root_move_only.py [--dry-run] [--no-upload]

After deploy, run: python scripts/fix_nginx_root_proxy.py
so nginx proxies / to the app (no redirect to /vidgenerator/).
"""
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

# Backend, app, scripts, docs touched for root move
ROOT_MOVE_FIXED = [
    "backend/routes/all_page_routes.py",
    "src/app/__init__.py",
    "vidgenerator/src/routes/advanced_calculator_routes.py",
    "vidgenerator/src/routes/point_calculator_routes.py",
    "fix_502.py",
    "scripts/ensure_site_up.py",
    "scripts/fix_502_nginx_only.py",
    "scripts/diagnose_https.py",
    "scripts/test_url_and_screenshot.py",
    "scripts/hard_fix_502.py",
    "scripts/fix_502_database.py",
    "scripts/warm_up_workers.py",
    "scripts/investigate_502.py",
    "scripts/fix_nginx_root_proxy.py",
    "scripts/test_and_debug_urls.py",
    "docs/DEPLOYMENT_PLAN.md",
    "docs/SERVER_QUICK_REFERENCE.md",
]


ROOT_PAGE_DIRS = (
    "static", "generator", "gallery", "shop", "battle", "chat", "debugger", "leaderboards", "quests",
    "news", "metal", "theme-points", "battlegrounds", "champions-league", "editor", "monetization",
    "milkyway", "rights-law", "victory-tech-tree", "danish-divine-tech-tree", "academic-perspective",
    "theme_premium", "time-achievement-guides", "beta_testing", "unified_dashboard", "advanced_calculator",
    "agent_support", "game", "lab", "stats", "social", "profile", "aggregator", "points", "trophies",
    "dashboard", "analytics", "compendium", "starmap25", "agents", "admin", "videos",
)


def collect_root_html_js():
    """Root-level HTML/JS (static/, page dirs, index.html, service-worker.js) for root move."""
    rels = []
    exclude = (".venv", "__pycache__", "node_modules", ".backup", "backup")
    for name in ["index.html", "service-worker.js"]:
        if (PROJECT_ROOT / name).is_file():
            rels.append(name)
    for top in ["static"] + [d for d in ROOT_PAGE_DIRS if (PROJECT_ROOT / d).is_dir()]:
        for p in (PROJECT_ROOT / top).rglob("*"):
            if not p.is_file():
                continue
            if p.suffix not in (".html", ".js"):
                continue
            parts = p.relative_to(PROJECT_ROOT).parts
            if any(part in exclude or "backup" in part.lower() for part in parts):
                continue
            rels.append(str(p.relative_to(PROJECT_ROOT)).replace(os.sep, "/"))
    return sorted(rels)


def collect_root_move_files():
    """All files to deploy for root move only."""
    fixed = [f for f in ROOT_MOVE_FIXED if (PROJECT_ROOT / f).exists()]
    root_html_js = collect_root_html_js()
    combined = list(dict.fromkeys(fixed + root_html_js))
    return sorted(combined)


def main():
    # Reuse deploy_all_and_restart_uwsgi's run()
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.deploy_all_and_restart_uwsgi import run

    import argparse
    ap = argparse.ArgumentParser(description="Deploy only root-move edited files and restart uwsgi-vidgenerator")
    ap.add_argument("--dry-run", action="store_true", help="Do not upload or restart; show planned steps")
    ap.add_argument("--no-upload", action="store_true", help="Do not upload; only restart uwsgi-vidgenerator")
    args = ap.parse_args()

    files = collect_root_move_files()
    print(f"Root-move deploy: {len(files)} files (backend, src, vidgenerator HTML/JS, scripts, docs)")
    if args.dry_run and files:
        for f in files[:30]:
            print(f"  {f}")
        if len(files) > 30:
            print(f"  ... and {len(files) - 30} more")
    ok = run(
        files,
        dry_run=args.dry_run,
        no_upload=args.no_upload,
        skip_gunicorn_check=False,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

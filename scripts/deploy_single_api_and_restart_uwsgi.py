#!/usr/bin/env python3
"""
Deploy only the files changed for the single-API (no /vidgenerator/api) switch, then restart uwsgi.
Faster than full deploy. Usage: python scripts/deploy_single_api_and_restart_uwsgi.py
"""
import sys
import importlib.util
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

# Files we changed for single-API: backend middleware, routes, services, generator, vidgenerator routes, docs
SINGLE_API_FILES = [
    "backend/middleware/skip_api_for_pages_middleware.py",
    "backend/middleware/auto_fix_404_middleware.py",
    "backend/middleware/response_cache_middleware.py",
    "backend/middleware/signal_processor_middleware.py",
    "backend/routes/generator_routes.py",
    "backend/routes/trophies_routes.py",
    "backend/routes/missing_endpoints_routes.py",
    "backend/routes/gallery_routes.py",
    "backend/routes/debugger_download.py",
    "backend/routes/agent_electric_magnet_routes.py",
    "backend/services/path_corrector.py",
    "backend/services/video_generator_service.py",
    "backend/services/agent_support_service.py",
    "generator/index.html",
    "vidgenerator/src/routes/point_calculator_routes.py",
    "vidgenerator/src/routes/advanced_calculator_routes.py",
    "docs/API_DOCUMENTATION.md",
    "docs/AGENTS_SKILLS_SYNC.md",
    "docs/PASSWORD_PROTECTION.md",
    "docs/INTELLIGENCE_SOURCES.md",
    "docs/SOCIAL_STRUCTURE.md",
    "docs/GENERATOR_AND_AI_OVERVIEW.md",
    "docs/SERVER_QUICK_REFERENCE.md",
    "docs/PORT_5000_BOTTLENECK_AND_SOLUTIONS.md",
]

def main():
    # Add all backend/routes/*.py (we removed vidgenerator decorators from all of them)
    all_files = list(SINGLE_API_FILES)
    backend_routes = PROJECT_ROOT / "backend" / "routes"
    if backend_routes.exists():
        for f in backend_routes.glob("*.py"):
            rel = str(f.relative_to(PROJECT_ROOT)).replace("\\", "/")
            if rel not in all_files:
                all_files.append(rel)

    files = [f for f in all_files if (PROJECT_ROOT / f).exists()]
    print(f"Deploying {len(files)} files (single-API changes + all backend routes), then restarting uwsgi...")

    spec = importlib.util.spec_from_file_location("deploy_all", SCRIPT_DIR / "deploy_all_and_restart_uwsgi.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ok = mod.run(files, dry_run=False, no_upload=False, skip_gunicorn_check=False)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()

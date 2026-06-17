"""Delete unused .py files (root one-offs, archived scripts, unreferenced scripts/)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", ".venv", "venv", "node_modules", ".pytest-tmp", "__pycache__"}

ROOT_KEEP = {
    "deploy.py",
    "fix_502.py",
    "deploy_ssh_env.py",
    "run.py",
    "wsgi.py",
}

PROTECTED_PREFIXES = ("backend/", "tests/", "migrations/")

CANONICAL_SCRIPTS = {
    "scripts/deploy.py",
    "scripts/check.py",
    "scripts/server_cleanup_scan.py",
    "scripts/clear_pyc_restart.py",
    "scripts/cleanup_obsolete_docs.py",
    "scripts/cleanup_unused_py.py",
    "scripts/post_deploy_verify.py",
    "scripts/sync_database_migration.py",
    "scripts/mn2_reconcile.py",
    "scripts/mn2_enable_staking.py",
    "scripts/mn2_recover_pending_commits.py",
    "scripts/treasury_signoff.py",
    "scripts/treasury_signoff_remote.py",
    "scripts/treasury_signoff_post.py",
    "scripts/treasury_signoff_post_ssh.py",
    "scripts/trader_staking_remote.py",
    "scripts/restart_uwsgi_fix_502.py",
    "scripts/restart_all_uwsgi.py",
    "scripts/agent_daemon.py",
    "scripts/service_check_all_components.py",
    "scripts/monetization_scr_export.py",
    "scripts/scr_usage_export.py",
    "scripts/process_webhook_outbox.py",
    "scripts/unified_points_drift_watch.py",
    "scripts/verify_mn2_production_ready.py",
    "scripts/generator_pricing_tune.py",
    "scripts/battle_migration.py",
    "scripts/post_deploy_verify.py",
    "scripts/test_all_button_endpoints.py",
    "scripts/test_tab_pages_e2e.py",
    "scripts/verify_tab_pages_live.py",
    "scripts/smoke_pages_game_battle.py",
    "scripts/smoke_profile_user_flows.py",
    "scripts/browser_smoke_profile_user.py",
    "scripts/shop_v4_production_smoke.py",
    "scripts/agent_mn2_shop_demo.py",
    "scripts/backfill_customer_avatars.py",
    "scripts/generate_agent_avatars.py",
    "scripts/cleanup_videos_keep_top10.py",
    "scripts/uwsgi_diagnose_server.sh",
    "scripts/force_uwsgi_reload.py",
    "scripts/restart_uwsgi.py",
    "scripts/init_database.py",
    "scripts/deploy_upload_update.py",
    "scripts/fix_gateways.py",
    "scripts/fix_nginx_proxy_all_pages.py",
    "scripts/read_pipeline.py",
    "scripts/check.py",
    "scripts/check_server.py",
    "scripts/check_routes.py",
    "scripts/diagnose_404.py",
    "scripts/deploy_finish.py",
    "scripts/check_flask_log.py",
}

REF_PATTERNS = [
    re.compile(r'["\']((?:backend|scripts|migrations|tests)/[a-zA-Z0-9_./-]+\.py)["\']'),
    re.compile(r'["\'](scripts/[a-zA-Z0-9_./-]+\.py)["\']'),
    re.compile(r"python\s+((?:scripts/)?[a-zA-Z0-9_./-]+\.py)"),
]


def collect_referenced_scripts() -> set[str]:
    refs: set[str] = set(CANONICAL_SCRIPTS)
    scan = {".py", ".md", ".sh", ".service", ".html", ".json", ".yml", ".yaml", ".txt", ".ini"}
    for p in ROOT.rglob("*"):
        if not p.is_file() or SKIP_PARTS.intersection(p.parts):
            continue
        if p.suffix.lower() not in scan and p.name not in {"Makefile", "Procfile", "deploy.py"}:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pat in REF_PATTERNS:
            for m in pat.findall(text):
                path = m.replace("\\", "/")
                if path.startswith("scripts/") or path.startswith("backend/"):
                    refs.add(path)
                elif path.endswith(".py") and "/" not in path:
                    refs.add(f"scripts/{path}")
    return refs


def iter_deletable() -> list[Path]:
    refs = collect_referenced_scripts()
    out: list[Path] = []

    # archive/
    archive = ROOT / "scripts" / "archive"
    if archive.exists():
        for p in archive.rglob("*.py"):
            out.append(p)

    # root one-offs
    for p in ROOT.glob("*.py"):
        if p.name not in ROOT_KEEP:
            out.append(p)

    # scripts not referenced
    scripts_dir = ROOT / "scripts"
    for p in scripts_dir.rglob("*.py"):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith("scripts/archive/"):
            continue
        if rel in {
            "scripts/cleanup_unused_py.py",
        }:
            continue
        if rel in refs:
            continue
        # basename match in refs
        if p.name in {Path(x).name for x in refs} and any(
            r.endswith("/" + p.name) or r == p.name for r in refs
        ):
            continue
        out.append(p)

    # stale vidgenerator/src legacy
    for p in (ROOT / "vidgenerator" / "src").rglob("*.py") if (ROOT / "vidgenerator" / "src").exists() else []:
        out.append(p)

    return sorted(set(out))


def main(dry_run: bool = False) -> None:
    targets = iter_deletable()
    print(f"{'DRY RUN — ' if dry_run else ''}Delete {len(targets)} .py files")
    for p in targets:
        rel = p.relative_to(ROOT).as_posix()
        print(f"  - {rel}")
        if not dry_run:
            p.unlink()
    # remove empty archive dir artifacts
    archive = ROOT / "scripts" / "archive"
    if not dry_run and archive.exists():
        for p in sorted(archive.rglob("*"), reverse=True):
            if p.is_file():
                continue
            try:
                p.rmdir()
            except OSError:
                pass
        readme = archive / "README.md"
        if readme.is_file():
            readme.unlink()
            try:
                archive.rmdir()
            except OSError:
                pass


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)

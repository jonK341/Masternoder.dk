"""Remove obsolete docs (session reports, duplicate summaries) from docs/."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SKIP_PARTS = {".git", ".pytest-tmp", "node_modules", ".venv"}
REF_PAT = re.compile(r"docs[/\\][A-Za-z0-9_./-]+\.(?:md|json|txt)", re.I)

# Always keep — active plans, ops, indexes, OpenAPI, db/, plans/, brainstorms/
KEEP_NAMES = {
    "PLAN.md",
    "README_GUIDES.md",
    "API_DOCUMENTATION.md",
    "DEPLOYMENT.md",
    "DEPLOYMENT_PLAN.md",
    "PROJECT_RETHINK.md",
    "MN2_TODO.md",
    "MN2_OPS.md",
    "PLATFORM_TODO.md",
    "RULEBOOK_CANON.md",
    "LAB.md",
    "CONTROL_BOARD_REPORT.md",
    "CONTROL_BOARD_REPORT.json",
    "API_COLLECTION.postman_collection.json",
}

KEEP_PREFIXES = ("docs/plans/", "docs/archive/plans/", "docs/db/", "docs/brainstorms/")

# Filename patterns → obsolete session / closeout artifacts
DELETE_PATTERNS = [
    re.compile(r"_COMPLETE\.md$", re.I),
    re.compile(r"_FIXED\.md$", re.I),
    re.compile(r"_FIXES_COMPLETE\.md$", re.I),
    re.compile(r"^ALL_.*\.md$", re.I),
    re.compile(r"^FINAL_.*\.md$", re.I),
    re.compile(r"^FIXES_.*\.md$", re.I),
    re.compile(r"^REMAINING_.*\.md$", re.I),
    re.compile(r"^PHASE[0-9].*\.md$", re.I),
    re.compile(r"^NEXT_STEPS_.*\.md$", re.I),
    re.compile(r"^SPRINT.*\.md$", re.I),
    re.compile(r"^DEBUGGER_.*\.md$", re.I),
    re.compile(r"^ERROR_.*\.md$", re.I),
    re.compile(r"^ONBOARDING_.*\.md$", re.I),
    re.compile(r"^DATABASE_(?!HEALTH).*\.md$", re.I),
    re.compile(r"^AGENT_.*\.md$", re.I),
    re.compile(r"^AGENTS_ARE_REAL_PLAYERS\.md$", re.I),
    re.compile(r"^AUTO_FIX_.*\.md$", re.I),
    re.compile(r"^AUTOMATION_ACTIVATED\.md$", re.I),
    re.compile(r"^MASTER_.*\.md$", re.I),
    re.compile(r"^MANAGER_.*\.md$", re.I),
    re.compile(r"^NEW_AGENTS_.*\.md$", re.I),
    re.compile(r"^NEW_PROBLEMS_.*\.md$", re.I),
    re.compile(r"^PROBLEMS_FIXED.*\.md$", re.I),
    re.compile(r"^PRODUCTION_(DEPLOYMENT_COMPLETE|AGENT_EXECUTION)\.md$", re.I),
    re.compile(r"^INTEGRATION_COMPLETE\.md$", re.I),
    re.compile(r"^HUNTERS_GAME_.*\.md$", re.I),
    re.compile(r"^UNIFIED_POINTS_.*_COMPLETE\.md$", re.I),
    re.compile(r"^MISSING_TABLES_.*\.md$", re.I),
    re.compile(r"^DEFAULT_USER_.*\.md$", re.I),
    re.compile(r"^COMPREHENSIVE_.*\.md$", re.I),
    re.compile(r"^COMPLETION_.*\.md$", re.I),
    re.compile(r"^COMPLETE_.*\.md$", re.I),
    re.compile(r"^A_PLUS_.*\.md$", re.I),
    re.compile(r"^ACTIVATION_.*\.md$", re.I),
    re.compile(r"^AGGRESSIVE_.*\.md$", re.I),
    re.compile(r"^CACHE_FIX_.*\.md$", re.I),
    re.compile(r"^DICT_FALLBACK_.*\.md$", re.I),
    re.compile(r"^VERIFICATION_.*\.md$", re.I),
    re.compile(r"^PYTHON_SKILLS_.*\.md$", re.I),
    re.compile(r"^PLAN_COMPLETE\.md$", re.I),
    re.compile(r"^FILE_INVENTORY_.*\.md$", re.I),
    re.compile(r"^endpoint_test_results\.txt$", re.I),
    re.compile(r"^NCIXG_.*\.md$", re.I),
    re.compile(r"^PLUGIN_.*\.md$", re.I),
    re.compile(r"^POINT_TABLES_.*\.md$", re.I),
    re.compile(r"^POINTS_PAGE_.*\.md$", re.I),
    re.compile(r"^URL_FIXES_.*\.md$", re.I),
    re.compile(r"^BROWSER_UI_.*\.md$", re.I),
    re.compile(r"^BACKEND_FRONTEND_.*\.md$", re.I),
    re.compile(r"^FUNCTIONS_AND_LOADING_.*\.md$", re.I),
    re.compile(r"^GENERATOR_ENHANCED_.*\.md$", re.I),
    re.compile(r"^LOADING_PERFORMANCE_.*\.md$", re.I),
    re.compile(r"^SERVER_LOCAL_.*\.md$", re.I),
    re.compile(r"^TROPHY_PAGE_HARD_.*\.md$", re.I),
    re.compile(r"^TROPHY_SYSTEM_AND_POINTS_COMPLETE\.md$", re.I),
    re.compile(r"^USER_PROFILE_AGENT_.*\.md$", re.I),
    re.compile(r"^50_AGENT_.*\.md$", re.I),
    re.compile(r"^AI_ENHANCEMENT_.*\.md$", re.I),
    re.compile(r"^CURRENT_STATUS\.md$", re.I),
    re.compile(r"^DEPLOYMENT_USER_PROFILE_.*\.md$", re.I),
    re.compile(r"^DEPLOYMENT_GUIDE\.md$", re.I),  # duplicate of DEPLOYMENT.md
    re.compile(r"^FINAL_CONCLUSION\.md$", re.I),
    re.compile(r"^PHD_FINAL_CONCLUSION\.md$", re.I),
    re.compile(r"^IMPLEMENTATION_TODO\.md$", re.I),  # superseded by PLATFORM_TODO / MN2_TODO
    re.compile(r"^FINAL_CONCLUSION\.md$", re.I),
    re.compile(r"^PHD_FINAL_CONCLUSION\.md$", re.I),
    re.compile(r"^COMPLETE_SYSTEM_SUMMARY\.md$", re.I),
    re.compile(r"^LOOSE_ENDS_PLAN\.md$", re.I),
    re.compile(r"^PLAN_COMPLETE\.md$", re.I),
    re.compile(r"^ERRORS_FIXED_AND_TABLES_CREATED\.md$", re.I),
    re.compile(r"^FRONTEND_REGENERATION_SUMMARY\.md$", re.I),
    re.compile(r"^HUNTERS_STAR_MAP_IMPLEMENTATION_SUMMARY\.md$", re.I),
    re.compile(r"^MISSING_FILES_AND_INTEGRATIONS_RECAP\.md$", re.I),
    re.compile(r"^QUICK_ISSUES_OVERVIEW\.md$", re.I),
    re.compile(r"^CODE_QUALITY_ANALYSIS\.md$", re.I),
    re.compile(r"^API_MONITORING_.*\.md$", re.I),
    re.compile(r"^API_SCANNER_.*\.md$", re.I),
    re.compile(r"^CALCULATOR_.*\.md$", re.I),
    re.compile(r"^ADVANCED_CALCULATOR_.*\.md$", re.I),
    re.compile(r"^404_FIXES_.*\.md$", re.I),
    re.compile(r"^AI_ENHANCEMENT_.*\.md$", re.I),
]

# Root-level stray plans / one-off reports
ROOT_DELETE = [
    "AGGREGATOR_INTELLIGENCE_RECAP_PLAN.md",
    "AGGREGATOR_INTELLIGENCE_INTEGRATION_PLAN.md",
]

ROOT_MOVE_TO_DOCS = {
    "SHOP_PURCHASE_MIGRATION_PLAN.md": "docs/SHOP_PURCHASE_MIGRATION_PLAN.md",
}

OTHER_DELETE = [
    "reports/dead_api_blueprint_route_audit.md",
    "reports/dead_api_blueprint_route_audit.json",
    "scripts/doc_refs_report.txt",
]


# Only treat references from code/UI/deploy as "live" — doc-to-doc links among
# session reports should not block cleanup.
REF_SOURCE_PARTS = {
    "backend",
    "scripts",
    "data",
    "lab",
    "shop",
    "battle",
    "debugger",
    "agents",
    "deploy.py",
    "fix_502.py",
    ".cursor",
}


def collect_referenced_docs() -> set[str]:
    refs: set[str] = set()
    for p in ROOT.rglob("*"):
        if not p.is_file() or SKIP_PARTS.intersection(p.parts):
            continue
        rel_parts = set(p.relative_to(ROOT).parts)
        if p.suffix.lower() not in {".py", ".html", ".json", ".mdc", ".js", ".ts", ".tsx"}:
            if p.name not in {"deploy.py", "fix_502.py"}:
                continue
        # Skip docs-only sources (except cursor rules)
        if "docs" in rel_parts and ".cursor" not in rel_parts:
            continue
        if not (rel_parts & REF_SOURCE_PARTS) and p.name not in {"deploy.py", "fix_502.py"}:
            if not any(str(p).endswith(x) for x in (".html",)):
                continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in REF_PAT.findall(text):
            refs.add(m.replace("\\", "/"))
    for deploy in (ROOT / "deploy.py", ROOT / "scripts" / "deploy.py"):
        if deploy.exists():
            text = deploy.read_text(encoding="utf-8", errors="ignore")
            for m in re.findall(r'"(docs/[^"]+)"', text):
                refs.add(m)
    return refs


def should_delete(rel: str, name: str, refs: set[str]) -> bool:
    if rel.startswith(KEEP_PREFIXES):
        return False
    if name in KEEP_NAMES:
        return False
    if rel in refs:
        return False
    return any(p.search(name) for p in DELETE_PATTERNS)


def main(dry_run: bool = False) -> None:
    refs = collect_referenced_docs()
    removed: list[str] = []
    moved: list[tuple[str, str]] = []

    for p in sorted(DOCS.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if should_delete(rel, p.name, refs):
            removed.append(rel)
            if not dry_run:
                p.unlink()

    for name in ROOT_DELETE:
        p = ROOT / name
        if p.is_file():
            removed.append(name)
            if not dry_run:
                p.unlink()

    for src, dst in ROOT_MOVE_TO_DOCS.items():
        sp = ROOT / src
        dp = ROOT / dst
        if sp.is_file() and not dp.exists():
            moved.append((src, dst))
            if not dry_run:
                dp.parent.mkdir(parents=True, exist_ok=True)
                sp.rename(dp)

    for rel in OTHER_DELETE:
        p = ROOT / rel
        if p.is_file():
            removed.append(rel)
            if not dry_run:
                p.unlink()

    print(f"{'DRY RUN — ' if dry_run else ''}Removed {len(removed)} files")
    for r in removed:
        print(f"  - {r}")
    if moved:
        print(f"Moved {len(moved)} files")
        for s, d in moved:
            print(f"  {s} -> {d}")


if __name__ == "__main__":
    import sys

    main(dry_run="--dry-run" in sys.argv)

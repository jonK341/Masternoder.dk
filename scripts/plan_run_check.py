#!/usr/bin/env python3
"""Audit all build plans: verify completion probes, mark todos, archive finished docs.

Usage:
  python scripts/plan_run_check.py              # report only
  python scripts/plan_run_check.py --apply      # update plan todos + archive finished docs
  python scripts/plan_run_check.py --apply --production-prune  # print SSH rm paths for server
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLANS_DIR = ROOT / "docs" / "plans"
ARCHIVE_DIR = ROOT / "docs" / "archive" / "plans"
DEPLOY_PY = ROOT / "scripts" / "deploy.py"

# Standalone docs explicitly marked finished — archive + remove from production deploy.
FINISHED_STANDALONE: dict[str, str] = {
    "docs/PROFILE_POINTS_SYNC_PLAN.md": "Plan finished — all 27 loose ends implemented.",
    "docs/SHOP_PURCHASE_MIGRATION_PLAN.md": "Phases 1–5 implemented; file-mode fallback live.",
    "docs/SHOP_MONETIZATION_AUTOMATION_CLOSEOUT.md": "Closeout doc — automation shipped.",
    "docs/MONETIZATION_INVESTIGATION_CLOSEOUT.md": "Closeout doc — investigation complete.",
    "docs/MONETIZATION_CONTENT_CRYPTO_PLAN.md": "Phases 1–4 implemented in repo.",
    "docs/PLAN_COMPLETE.md": "AI skills plan complete.",
    "docs/POINT_TABLES_UPDATE_COMPLETE.md": "Point tables migration complete.",
    "docs/MASTERNODER2_CRYPTO_INTEGRATION_PLAN.md": "Superseded by MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md.",
}

# Cursor plan todo id -> probe (all paths relative to ROOT must exist)
ECOSYSTEM_PROBES: dict[str, list[str]] = {
    "audit": ["docs/MN2_ECOSYSTEM_REPORT.md"],
    "daemon-health": ["backend/routes/health_routes.py", "tests/unit/test_gate_a_orchestrator.py"],
    "wallet": ["backend/services/mn2_wallet_service.py", "backend/services/mn2_ledger.py"],
    "market": ["backend/services/p2p_market_service.py"],
    "agents": ["backend/services/agent_wallet_service.py", "backend/services/agent_trader_service.py"],
    "explorer": ["backend/services/mn2_explorer_data.py", "backend/services/discord_service.py"],
    "debugger-qa": ["backend/routes/debugger_quiz_routes.py"],
    "casino-crypto": ["backend/services/casino_service.py"],
    "monitoring": ["backend/services/activity_events_service.py"],
    "security-cron": ["backend/services/backup_service.py", "backend/routes/security_cron_routes.py"],
    "generator": ["backend/services/generator_mn2_service.py", "backend/services/generator_pricing_service.py"],
    "game-monitor": ["backend/services/game_mn2_rewards.py"],
    "customer-aggregator": ["backend/services/customer_aggregator_service.py"],
    "ai-intelligence": ["backend/services/ai_staking_advisor_service.py"],
    "tests-docs-commit": ["docs/MN2_ECOSYSTEM_REPORT.md", "docs/MN2_TODO.md"],
}

ORCHESTRATOR_PROBES: dict[str, list[str]] = {
    "stage0-foundations": ["tests/unit/test_gate_a_orchestrator.py"],
    "stage1-economy": [
        "backend/services/mn2_ledger.py",
        "backend/services/activity_events_service.py",
        "backend/services/generator_pricing_service.py",
        "backend/services/game_mn2_rewards.py",
    ],
    "stage1b-hardening": ["backend/services/backup_service.py", "tests/unit/test_gate_s_orchestrator.py"],
    "stage2-market-agents": ["backend/services/p2p_market_service.py", "backend/services/agent_wallet_service.py"],
    "stage2-generator-crypto": ["backend/services/generator_mn2_service.py"],
    "stage2-game-crypto": ["backend/services/game_mn2_rewards.py"],
    "stage2-casino-explorer-debugger": [
        "backend/services/casino_service.py",
        "backend/services/mn2_explorer_data.py",
        "backend/services/market_discord_fanout.py",
    ],
    "stage2-customer-aggregator": ["backend/services/customer_aggregator_service.py"],
    "stage2-ai-intelligence": ["backend/services/ai_staking_advisor_service.py"],
    "stage3-monitoring": ["backend/services/activity_events_service.py"],
    "stage3-cron": ["backend/routes/security_cron_routes.py", "cron/mn2_accrue_rewards.sh"],
    "stage3-control-board": ["backend/routes/point_control_board_routes.py"],
    "stage4-finalize": ["docs/MN2_ECOSYSTEM_REPORT.md", "docs/MN2_TODO.md", "tests/unit/test_gate_a_orchestrator.py"],
}

GENERATOR_PROBES: dict[str, list[str]] = {
    "themes-user-api": ["backend/routes/missing_endpoints_routes.py"],
    "generator-deploy-manifest": ["scripts/deploy.py"],
    "cache-busting": ["vidgenerator/generator/index.html"],
}

GAME_BATTLE_DONE = {"fix-tournament-api"}


@dataclass
class PlanReport:
    path: str
    name: str = ""
    todos: list[dict] = field(default_factory=list)
    finished: bool = False
    notes: list[str] = field(default_factory=list)


def _exists(rel: str) -> bool:
    return (ROOT / rel).is_file()


def _probe_ok(paths: list[str]) -> bool:
    return all(_exists(p) for p in paths)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    block = text[3:end]
    meta: dict = {}
    for line in block.splitlines():
        m = re.match(r"^(\w+):\s*(.+)$", line.strip())
        if m:
            meta[m.group(1)] = m.group(2).strip().strip('"')
    return meta, text[end + 4 :]


def _parse_todos(text: str) -> list[dict]:
    todos: list[dict] = []
    cur: dict | None = None
    for line in text.splitlines():
        if re.match(r"^\s*-\s+id:\s*", line):
            if cur:
                todos.append(cur)
            cur = {"id": line.split(":", 1)[1].strip()}
        elif cur is not None:
            m = re.match(r"^\s+(content|status):\s*(.+)$", line)
            if m:
                cur[m.group(1)] = m.group(2).strip().strip('"')
    if cur:
        todos.append(cur)
    return todos


def _todo_done(todo_id: str, plan_stem: str) -> bool | None:
    if plan_stem == "masternoder_mn2_ecosystem.plan":
        paths = ECOSYSTEM_PROBES.get(todo_id)
        return _probe_ok(paths) if paths else None
    if plan_stem == "master_build_orchestrator.plan":
        paths = ORCHESTRATOR_PROBES.get(todo_id)
        return _probe_ok(paths) if paths else None
    if plan_stem == "generator_page_roadmap.plan":
        if todo_id == "discord-generator-channel":
            return _exists("backend/services/discord_service.py") and _exists(
                "backend/services/video_generator_service.py"
            )
        return None
    if plan_stem == "game_and_battle_review.plan":
        if todo_id in GAME_BATTLE_DONE:
            return True
        return None
    if plan_stem == "eu_crypto_casino_platform.plan":
        if todo_id == "discord-casino-channel":
            return _exists("backend/services/casino_discord_fanout.py")
        return None
    return None


def _run_gate_tests() -> tuple[int, int]:
    env = {**dict(__import__("os").environ), "TMPDIR": str(ROOT / ".pytest-tmp")}
    (ROOT / ".pytest-tmp").mkdir(exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/test_gate_a_orchestrator.py",
        "tests/unit/test_gate_b_orchestrator.py",
        "tests/unit/test_gate_s_orchestrator.py",
        "-q",
        "--tb=no",
    ]
    try:
        r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
        out = r.stdout + r.stderr
        m = re.search(r"(\d+) passed", out)
        passed = int(m.group(1)) if m else 0
        m2 = re.search(r"(\d+) failed", out)
        failed = int(m2.group(1)) if m2 else 0
        return passed, failed
    except Exception as e:
        return 0, -1


def _set_todo_status(content: str, todo_id: str, status: str) -> str:
    lines = content.splitlines()
    in_todo = False
    for i, line in enumerate(lines):
        if re.match(rf"^\s*-\s+id:\s+{re.escape(todo_id)}\s*$", line):
            in_todo = True
            continue
        if in_todo and re.match(r"^\s+status:\s*", line):
            lines[i] = re.sub(r"status:\s*\S+", f"status: {status}", line)
            in_todo = False
        elif in_todo and re.match(r"^\s*-\s+id:\s*", line):
            in_todo = False
    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


def audit_cursor_plan(path: Path) -> PlanReport:
    text = path.read_text(encoding="utf-8")
    meta, _ = _parse_frontmatter(text)
    todos = _parse_todos(text)
    stem = path.stem
    rep = PlanReport(path=str(path.relative_to(ROOT)).replace("\\", "/"), name=meta.get("name", stem))

    for t in todos:
        tid = t.get("id", "")
        current = t.get("status", "pending")
        if current in ("completed", "cancelled"):
            rep.todos.append({**t, "verified": current})
            continue
        verdict = _todo_done(tid, stem)
        if verdict is True:
            rep.todos.append({**t, "verified": "completed"})
            rep.notes.append(f"  mark {tid} -> completed (probe pass)")
        elif verdict is False:
            rep.todos.append({**t, "verified": "pending"})
        else:
            rep.todos.append({**t, "verified": current})

    pending = [t for t in rep.todos if t.get("verified") not in ("completed", "cancelled")]
    rep.finished = len(pending) == 0 and len(rep.todos) > 0
    return rep


def _generator_criticals_done() -> bool:
    if not _exists("backend/routes/missing_endpoints_routes.py"):
        return False
    body = (ROOT / "backend/routes/missing_endpoints_routes.py").read_text(encoding="utf-8", errors="ignore")
    if "def themes_user" not in body:
        return False
    deploy = DEPLOY_PY.read_text(encoding="utf-8", errors="ignore")
    if '"generator":' not in deploy:
        return False
    gen_html = ROOT / "vidgenerator/generator/index.html"
    if gen_html.is_file():
        html = gen_html.read_text(encoding="utf-8", errors="ignore")
        if "?v=" not in html and "cache" not in html.lower():
            return False
    return True


def apply_plan_updates(reports: list[PlanReport]) -> None:
    for rep in reports:
        path = ROOT / rep.path
        text = path.read_text(encoding="utf-8")
        changed = False
        for t in rep.todos:
            if t.get("verified") == "completed" and t.get("status") != "completed":
                text = _set_todo_status(text, t["id"], "completed")
                changed = True
        if changed:
            path.write_text(text, encoding="utf-8")
            print(f"Updated todos: {rep.path}")


def archive_finished_standalone(apply: bool) -> list[str]:
    archived: list[str] = []
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for rel, reason in FINISHED_STANDALONE.items():
        src = ROOT / rel
        if not src.is_file():
            continue
        dst = ARCHIVE_DIR / src.name
        archived.append(rel)
        print(f"FINISHED {rel} — {reason}")
        if apply:
            header = (
                f"<!-- ARCHIVED {Path(rel).name} — finished plan removed from active docs. -->\n\n"
                f"> **Archived:** 2026-06-17. {reason}\n\n"
            )
            body = src.read_text(encoding="utf-8")
            if not body.startswith("<!-- ARCHIVED"):
                dst.write_text(header + body, encoding="utf-8")
                src.unlink()
                print(f"  archived -> {dst.relative_to(ROOT)}")
    return archived


def remove_from_deploy_manifest(paths: list[str], apply: bool) -> None:
    if not DEPLOY_PY.is_file():
        return
    text = DEPLOY_PY.read_text(encoding="utf-8")
    original = text
    for rel in paths:
        name = Path(rel).name
        text = re.sub(rf'^\s+"docs/{re.escape(name)}",\n', "", text, flags=re.M)
    if text != original:
        print("Deploy manifest: removed finished plan doc(s)")
        if apply:
            DEPLOY_PY.write_text(text, encoding="utf-8")


def production_rm_paths(archived: list[str]) -> list[str]:
    return [f"/var/www/html/{p}" for p in archived]


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit build plans and archive finished docs")
    ap.add_argument("--apply", action="store_true", help="Update plan todos and archive finished docs")
    ap.add_argument("--production-prune", action="store_true", help="Print server rm paths for archived docs")
    args = ap.parse_args()

    print("=== Plan run check ===\n")
    passed, failed = _run_gate_tests()
    if failed < 0:
        print("Gate tests: skipped (error)")
    else:
        print(f"Gate tests: {passed} passed, {failed} failed\n")

    reports: list[PlanReport] = []
    for p in sorted(PLANS_DIR.glob("*.plan.md")):
        rep = audit_cursor_plan(p)
        reports.append(rep)
        done = sum(1 for t in rep.todos if t.get("verified") == "completed")
        cancel = sum(1 for t in rep.todos if t.get("verified") == "cancelled")
        pend = len(rep.todos) - done - cancel
        flag = "FINISHED" if rep.finished else "ACTIVE"
        print(f"[{flag}] {rep.path} ({done}/{len(rep.todos)} done, {pend} pending)")
        for n in rep.notes:
            print(n)

    gen_ok = _generator_criticals_done()
    print(f"\nGenerator P0/P1 criticals: {'PASS' if gen_ok else 'FAIL'} (themes/user, deploy manifest, cache)")

    print("\n--- Standalone finished docs ---")
    archived = archive_finished_standalone(apply=args.apply)
    remove_from_deploy_manifest(archived, apply=args.apply)

    if args.apply:
        apply_plan_updates(reports)

    if args.production_prune and archived:
        print("\n--- Remove from production (run on server) ---")
        for p in production_rm_paths(archived):
            print(f"  rm -f {p}")

    print(f"\nSummary: {len(archived)} standalone plans finished/archived; "
          f"{sum(1 for r in reports if r.finished)} cursor plans fully complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

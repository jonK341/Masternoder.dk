#!/usr/bin/env python3
"""
Investigate and remove leftover / outdated files on masternoder.dk (/var/www/html).

Usage:
  python scripts/server_orphan_scan.py                    # Investigation report only
  python scripts/server_orphan_scan.py --ask-pass         # Prompt for SSH password
  python scripts/server_orphan_scan.py --clean --yes      # Remove safe orphans (needs DEPLOY_PASS)
  python scripts/server_orphan_scan.py --clean --yes --ask-pass

Safe cleanup removes dev artifacts, old backup trees, stale shadow modules, deploy *.backup.* files,
orphan video metadata, __pycache__, and optional disk hygiene (nginx/apt/journal) when --with-disk is set.
Never touches data/, config/, instance/, .env, or runtime MN2 state files.
"""
from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

REMOTE_BASE = "/var/www/html"

# Stale modules that shadow src/app/__init__.py (see deploy.py STALE_REMOTE_FILES).
STALE_REMOTE_GLOBS = [
    "src/app.py",
    "src/app.pyc",
    "src/__pycache__/app*.pyc",
    "vidgenerator/src/app.py",
    "vidgenerator/src/app.pyc",
    "vidgenerator/src/__pycache__/app*.pyc",
]

# Top-level dirs that must never be on production (dev / local-only / old backups).
REMOVABLE_TOP_DIRS = frozenset({
    "removed_scripts_backup",
    "server_backup",
    "vidgenerator.backup",
    "backup_original",
    "backups",
    "node_modules",
    ".cursor",
    "mcps",
    ".pytest-tmp",
    ".pytest_tmp",
    ".pytest_cache",
    ".firecrawl",
    ".vscode",
    "scripts/archive",
})

# Glob patterns under REMOTE_BASE (shell find -path).
REMOVABLE_DIR_GLOBS = [
    "vidgenerator.backup.*",
    "*/node_modules",
    "*/.pytest-tmp",
    "*/.pytest_cache",
]

# Runtime paths — report but never delete.
PROTECTED_PREFIXES = (
    "data/",
    "config/",
    "instance/",
    ".env",
    "logs/mn2_",
)

# Finished plan docs — safe to remove from production (archived locally under docs/archive/plans/).
ARCHIVED_PLAN_DOCS = [
    "docs/PROFILE_POINTS_SYNC_PLAN.md",
    "docs/SHOP_PURCHASE_MIGRATION_PLAN.md",
    "docs/SHOP_MONETIZATION_AUTOMATION_CLOSEOUT.md",
    "docs/MONETIZATION_INVESTIGATION_CLOSEOUT.md",
    "docs/MONETIZATION_CONTENT_CRYPTO_PLAN.md",
    "docs/PLAN_COMPLETE.md",
    "docs/POINT_TABLES_UPDATE_COMPLETE.md",
    "docs/MASTERNODER2_CRYPTO_INTEGRATION_PLAN.md",
]

# Server-only paths that are OK even if absent from git checkout.
SERVER_RUNTIME_NAMES = frozenset({
    ".env",
    ".venv",
    "venv",
    "uwsgi.log",
    "flask_app.log",
    ".uwsgi_touch_reload",
    "uwsgi.ini",
    "uwsgi_common.ini",
    "uwsgi_5001.ini",
    "wsgi.py",
    "instance",
    "config",
    "videos",
    "uploads",
    "output",
    "exports",
    "recordings",
})


def run_cmd(ssh, cmd: str, timeout: int = 120) -> tuple[str, str]:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode(errors="replace").strip()
    err = (stderr.read() or b"").decode(errors="replace").strip()
    return out, err


def _local_top_level_names() -> set[str]:
    names: set[str] = set()
    skip = {".git", ".venv", "__pycache__"}
    for name in os.listdir(_ROOT):
        if name in skip or name.startswith("."):
            continue
        names.add(name)
    return names


def _section(title: str, lines: list[str]) -> list[str]:
    out = [f"\n[{title}]", "-" * 50]
    out.extend(lines or ["  (none)"])
    return out


def investigate(ssh) -> list[str]:
    report: list[str] = [
        "=" * 60,
        "SERVER ORPHAN / OUTDATED FILE INVESTIGATION — masternoder.dk",
        f"Web root: {REMOTE_BASE}",
        "=" * 60,
    ]

    out, _ = run_cmd(ssh, "df -h / 2>/dev/null | tail -2")
    report.extend(_section("DISK", [out or "(no df)"]))

    out, _ = run_cmd(ssh, f"du -sh {REMOTE_BASE}/* {REMOTE_BASE}/.[!.]* 2>/dev/null | sort -hr | head -35")
    report.extend(_section("LARGEST TOP-LEVEL UNDER /var/www/html", (out or "").splitlines()))

    # Removable dev/backup dirs
    removable_hits: list[str] = []
    for d in sorted(REMOVABLE_TOP_DIRS):
        out, _ = run_cmd(ssh, f"test -e {REMOTE_BASE}/{d} && du -sh {REMOTE_BASE}/{d} 2>/dev/null || true")
        if out:
            removable_hits.append(f"  {out}  ← safe to remove")
    out, _ = run_cmd(
        ssh,
        f"du -sh {REMOTE_BASE}/vidgenerator.backup.* 2>/dev/null || true",
    )
    for line in (out or "").splitlines():
        if line.strip():
            removable_hits.append(f"  {line.strip()}  ← safe to remove")
    report.extend(_section("REMOVABLE DEV / BACKUP DIRS", removable_hits))

    # Stale shadow modules
    stale_hits: list[str] = []
    for g in STALE_REMOTE_GLOBS:
        out, _ = run_cmd(ssh, f"ls -la {REMOTE_BASE}/{g} 2>/dev/null || true")
        for line in (out or "").splitlines():
            if line.strip() and not line.startswith("total"):
                stale_hits.append(f"  {REMOTE_BASE}/{g}  ({line.strip()[:80]})")
    report.extend(_section("STALE SHADOW MODULES (break imports)", stale_hits))

    # Deploy-time *.backup.YYYYMMDD_HHMMSS next to live files
    out, _ = run_cmd(
        ssh,
        f"find {REMOTE_BASE} -type f -name '*.backup.20*' 2>/dev/null | head -40",
    )
    backup_files = [f"  {p}" for p in (out or "").splitlines() if p.strip()]
    out2, _ = run_cmd(
        ssh,
        f"find {REMOTE_BASE} -type f -name '*.backup.20*' 2>/dev/null | wc -l",
    )
    n_backups = (out2 or "0").strip()
    if backup_files:
        backup_files.append(f"  ... total count: {n_backups}")
    report.extend(_section("DEPLOY SNAPSHOT FILES (*.backup.20*)", backup_files))

    # Top-level names on server not in local repo (excluding runtime)
    remote_out, _ = run_cmd(ssh, f"ls -1 {REMOTE_BASE} 2>/dev/null")
    remote_names = {x.strip() for x in (remote_out or "").splitlines() if x.strip()}
    local_names = _local_top_level_names()
    orphan_top = sorted(
        n for n in remote_names
        if n not in local_names and n not in SERVER_RUNTIME_NAMES and not n.startswith(".")
    )
    orphan_lines = [f"  {n}" for n in orphan_top] if orphan_top else []
    report.extend(_section("TOP-LEVEL ON SERVER BUT NOT IN LOCAL REPO", orphan_lines))

    # Legacy vidgenerator/ duplicate pages (root moved out of vidgenerator/)
    out, _ = run_cmd(
        ssh,
        f"for d in profile generator battle shop gallery game stats social lab trophies debugger; do "
        f"if test -d {REMOTE_BASE}/vidgenerator/$d && test -d {REMOTE_BASE}/$d; then "
        f"echo \"DUPLICATE: /$d and /vidgenerator/$d ($(du -sh {REMOTE_BASE}/vidgenerator/$d 2>/dev/null | cut -f1))\"; "
        f"fi; done",
    )
    dup_lines = [f"  {ln}" for ln in (out or "").splitlines() if ln.strip()]
    report.extend(_section("LEGACY vidgenerator/ DUPLICATE PAGE DIRS", dup_lines))

    # Orphan video metadata
    out, _ = run_cmd(
        ssh,
        "for d in /var/www/html/videos /var/www/html/vidgenerator/videos; do "
        "test -d \"$d\" || continue; "
        "echo \"--- $d ---\"; "
        "find \"$d\" -maxdepth 1 \\( -name '*.job.json' -o -name '*.pipeline.json' -o -name '*_temp_audio.mp4' \\) 2>/dev/null | wc -l; "
        "done",
    )
    report.extend(_section("ORPHAN VIDEO METADATA (count per dir)", (out or "").splitlines()))

    # Old logs (>30d) under app logs/
    out, _ = run_cmd(
        ssh,
        f"find {REMOTE_BASE}/logs -type f -mtime +30 2>/dev/null | wc -l",
    )
    n_old_logs = (out or "0").strip()
    out2, _ = run_cmd(
        ssh,
        f"find {REMOTE_BASE}/logs -type f -mtime +30 -size +1M 2>/dev/null | head -15",
    )
    log_lines = [f"  Files older than 30d: {n_old_logs}"]
    log_lines.extend(f"  {p}" for p in (out2 or "").splitlines() if p.strip())
    report.extend(_section("OLD APP LOGS (>30 days)", log_lines))

    # Archived finished plan docs (local copies in docs/archive/plans/)
    plan_hits: list[str] = []
    for rel in ARCHIVED_PLAN_DOCS:
        out, _ = run_cmd(ssh, f"test -f {REMOTE_BASE}/{rel} && ls -la {REMOTE_BASE}/{rel} 2>/dev/null || true")
        if out.strip():
            plan_hits.append(f"  {REMOTE_BASE}/{rel}  ← archived locally, safe to remove")
    report.extend(_section("ARCHIVED FINISHED PLAN DOCS ON SERVER", plan_hits))

    # .git on server (often accidental, large)
    out, _ = run_cmd(ssh, f"du -sh {REMOTE_BASE}/.git 2>/dev/null || echo ''")
    if out.strip():
        report.extend(_section(".git ON SERVER (review before delete)", [f"  {out.strip()}"]))

    report.extend([
        "",
        "=" * 60,
        "Run with --clean --yes to remove safe items listed above.",
        "Add --with-disk for nginx/apt/journal/__pycache__ (see server_cleanup_scan.py).",
        "=" * 60,
    ])
    return report


def _confirm(yes: bool, msg: str) -> bool:
    if yes:
        return True
    try:
        r = input(f"{msg} [y/N]: ")
        return r.strip().lower() == "y"
    except Exception:
        print("Non-interactive session — use --yes to confirm.")
        return False


def cleanup(ssh, *, yes: bool = False, with_disk: bool = False) -> list[str]:
    actions: list[str] = []
    if not _confirm(yes, "Remove safe orphaned/outdated files on server?"):
        print("Aborted.")
        return actions

    before_out, _ = run_cmd(ssh, "df --output=avail / 2>/dev/null | tail -1")
    try:
        before_kb = int(before_out.strip())
    except ValueError:
        before_kb = None

    for d in REMOVABLE_TOP_DIRS:
        run_cmd(ssh, f"rm -rf {REMOTE_BASE}/{d} 2>/dev/null; true")
    actions.append(f"Removed dev/backup top-level dirs: {', '.join(sorted(REMOVABLE_TOP_DIRS))}")

    run_cmd(ssh, f"rm -rf {REMOTE_BASE}/vidgenerator.backup.* 2>/dev/null; true")
    actions.append("Removed vidgenerator.backup.*")

    for g in STALE_REMOTE_GLOBS:
        run_cmd(ssh, f"rm -f {REMOTE_BASE}/{g} 2>/dev/null; true")
    actions.append("Removed stale src/app.py shadow files")

    run_cmd(ssh, f"find {REMOTE_BASE} -type f -name '*.backup.20*' -delete 2>/dev/null; true")
    actions.append("Removed deploy snapshot files (*.backup.20*)")

    # Orphan video metadata without matching .mp4
    run_cmd(
        ssh,
        "for d in /var/www/html/videos /var/www/html/vidgenerator/videos; do "
        "rm -f \"$d\"/*_temp_audio.mp4 2>/dev/null; "
        "cd \"$d\" 2>/dev/null && for f in *.job.json *.pipeline.json; do "
        "test -f \"$f\" || continue; b=\"${f%.job.json}\"; b=\"${b%.pipeline.json}\"; "
        "test -f \"$b.mp4\" || rm -f \"$f\"; done; done; true",
    )
    actions.append("Orphan video metadata/temp cleaned")

    run_cmd(
        ssh,
        f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null; "
        f"find {REMOTE_BASE} -type f -name '*.pyc' -delete 2>/dev/null; true",
    )
    actions.append("Python __pycache__ / .pyc cleared")

    for rel in ARCHIVED_PLAN_DOCS:
        run_cmd(ssh, f"rm -f {REMOTE_BASE}/{rel} 2>/dev/null; true")
    actions.append(f"Removed {len(ARCHIVED_PLAN_DOCS)} archived finished plan doc(s)")

    if with_disk:
        run_cmd(ssh, "rm -rf /var/cache/nginx/* 2>/dev/null; apt-get clean -y 2>/dev/null; journalctl --vacuum-time=3d 2>/dev/null; true")
        actions.append("Disk hygiene: nginx cache, apt clean, journal 3d")

    after_out, _ = run_cmd(ssh, "df --output=avail / 2>/dev/null | tail -1")
    try:
        after_kb = int(after_out.strip())
    except ValueError:
        after_kb = None
    if before_kb is not None and after_kb is not None and after_kb >= before_kb:
        freed = after_kb - before_kb
        if freed >= 1024:
            actions.append(f"Space freed: {freed / 1024:.1f} MB")
        else:
            actions.append(f"Space freed: {freed} KB")

    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description="Investigate/remove leftover files on masternoder.dk")
    parser.add_argument("--ask-pass", action="store_true", help="Prompt for SSH password (ignores stale .env)")
    parser.add_argument("--clean", action="store_true", help="Remove safe orphaned/outdated files after scan")
    parser.add_argument("--with-disk", action="store_true", help="With --clean: also nginx/apt/journal cleanup")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation for --clean")
    args = parser.parse_args()

    try:
        import paramiko
    except ImportError:
        print("pip install paramiko")
        return 1

    host = deploy_host()
    user = deploy_user()
    password = require_deploy_pass(force_prompt=args.ask_pass)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=password, timeout=30)
    except Exception as exc:
        print(f"SSH connection failed: {exc}")
        if not args.ask_pass:
            print("Hint: DEPLOY_PASS in .env may be stale — retry with --ask-pass")
        return 1

    try:
        report = investigate(ssh)
        print("\n".join(report))

        if args.clean:
            print("\n--- CLEANUP ---")
            for line in cleanup(ssh, yes=args.yes, with_disk=args.with_disk):
                print(f"  [OK] {line}")
            print("\nRe-run without --clean to verify.")
    finally:
        ssh.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

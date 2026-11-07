#!/usr/bin/env bash
# Pre-merge / pre-deploy checks: repo PRs, local merge state, optional server git health. <!-- pragma: allowlist secret -->
# Usage:
#   bash scripts/merge_preflight.sh
#   bash scripts/merge_preflight.sh --server   # requires DEPLOY_PASS
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

WITH_SERVER=0
if [[ "${1:-}" == "--server" ]]; then
  WITH_SERVER=1
fi

echo "=========================================="
echo "MERGE PREFLIGHT"
echo "=========================================="
date -Is
echo

fail=0

echo "[1] Local git"
if [[ -f .git/MERGE_HEAD ]]; then
  echo "  FAIL: merge in progress (MERGE_HEAD). Run git merge --abort or git commit."
  fail=1
else
  echo "  OK: no in-progress merge"
fi
if [[ -f .git/CHERRY_PICK_HEAD ]]; then
  echo "  FAIL: cherry-pick in progress"
  fail=1
fi
branch="$(git branch --show-current)"
echo "  branch: $branch"
echo "  HEAD: $(git log -1 --oneline)"
behind="$(git rev-list --count HEAD..origin/main 2>/dev/null || echo '?')"
ahead="$(git rev-list --count origin/main..HEAD 2>/dev/null || echo '?')"
echo "  vs origin/main: ahead $ahead, behind $behind"
echo

echo "[2] Open pull requests (gh)"
if command -v gh >/dev/null 2>&1; then
  pr_json="$(mktemp)"
  if gh pr list --state open --json number,title,mergeable,mergeStateStatus >"$pr_json" 2>/dev/null; then
    python3 - "$pr_json" <<'PY' || true
import json, sys
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    rows = json.load(f)
if not rows:
    print("  OK: no open PRs")
else:
    for r in rows:
        flag = "OK" if r.get("mergeable") == "MERGEABLE" and r.get("mergeStateStatus") == "CLEAN" else "WARN"
        title = (r.get("title") or "")[:60]
        print(f"  [{flag}] #{r['number']} {title} — {r.get('mergeStateStatus')}/{r.get('mergeable')}")
PY
  else
    echo "  WARN: gh pr list failed"
  fi
  rm -f "$pr_json"
else
  echo "  SKIP: gh not installed"
fi
echo

echo "[3] Requirements pins (Flask/Werkzeug vs Python 3.12+)"
python3 - <<'PY' 2>/dev/null || true
import re
from pathlib import Path
candidates = sorted(Path(".").glob("requirements-*.txt"), key=lambda p: p.name)
names = [p.name for p in candidates if "optional" not in p.name and p.name != "requirements_v3_upgraded.txt"]
if "requirements.txt" not in names:
    names.append("requirements.txt")
for name in names:
    p = Path(name)
    if not p.is_file():
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    flask = re.search(r"^Flask[=><].*$", text, re.M)
    werk = re.search(r"^Werkzeug[=><].*$", text, re.M)
    print(f"  {name}:")
    print(f"    {flask.group(0) if flask else 'Flask: (not found)'}")
    print(f"    {werk.group(0) if werk else 'Werkzeug: (not found)'}")
PY
echo

if [[ "$WITH_SERVER" -eq 1 ]]; then
  echo "[4] Server git (SSH)"
  if [[ -z "${DEPLOY_PASS:-}" ]]; then
    echo "  SKIP: DEPLOY_PASS unset"
  else
    PY_RUN="python3"
    if [[ -x "$ROOT/.venv/bin/python" ]]; then
      PY_RUN="$ROOT/.venv/bin/python"
    fi
    "$PY_RUN" - <<'PY' || fail=1
import os, sys
sys.path.insert(0, os.getcwd())
from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass
ssh, _, _ = connect_deploy_ssh(require_deploy_pass())
cmds = [
    "test -f /var/www/html/.git/MERGE_HEAD && echo MERGE_IN_PROGRESS || echo no_server_merge",
    "cd /var/www/html && git log -1 --oneline",
    "cd /var/www/html && git status -sb | head -5",
]
for c in cmds:
    _, so, _ = ssh.exec_command(c, timeout=30)
    print(" ", so.read().decode(errors="replace").strip())
ssh.close()
PY
  fi
  echo
fi

echo "=========================================="
if [[ "$fail" -ne 0 ]]; then
  echo "PREFLIGHT: FAILED"
  exit 1
fi
echo "PREFLIGHT: OK (review WARN lines before merging)"
exit 0

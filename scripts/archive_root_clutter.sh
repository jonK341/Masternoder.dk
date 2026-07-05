#!/bin/bash
# Archive root-level clutter into archive/ — safe to re-run.
# Keeps: wsgi.py, run.py, deploy.py, fix_502.py, deploy_ssh_env.py, README.md
# Usage: bash scripts/archive_root_clutter.sh [--dry-run]

set -u
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVE="$ROOT/archive/root-cleanup-$(date +%Y%m%d)"
KEEP_PY="wsgi.py run.py deploy.py fix_502.py deploy_ssh_env.py"

run() {
  if [[ $DRY_RUN -eq 1 ]]; then echo "[dry-run] $*"; else eval "$@"; fi
}

echo "=== Archive root clutter → $ARCHIVE ==="
run mkdir -p "$ARCHIVE/scripts" "$ARCHIVE/reports" "$ARCHIVE/docs" "$ARCHIVE/deployments"

# One-off Python scripts at root
for f in "$ROOT"/*.py; do
  [[ -f "$f" ]] || continue
  base=$(basename "$f")
  skip=0
  for k in $KEEP_PY; do [[ "$base" == "$k" ]] && skip=1; done
  [[ $skip -eq 1 ]] && continue
  run mv "$f" "$ARCHIVE/scripts/"
done

# Test/report JSON at root
for f in "$ROOT"/*.json; do
  [[ -f "$f" ]] || continue
  run mv "$f" "$ARCHIVE/reports/"
done

# Status markdown at root (keep README)
for f in "$ROOT"/*.md; do
  [[ -f "$f" ]] || continue
  [[ "$(basename "$f")" == "README.md" ]] && continue
  run mv "$f" "$ARCHIVE/docs/"
done

# Old deployment tarballs
for f in "$ROOT"/deployment*.tar.gz; do
  [[ -f "$f" ]] || continue
  run mv "$f" "$ARCHIVE/deployments/"
done

# Misc text artifacts
for f in "$ROOT"/*_list.txt "$ROOT"/*_report.txt "$ROOT"/audit_after_fixes.txt; do
  [[ -f "$f" ]] || continue
  run mv "$f" "$ARCHIVE/reports/"
done

echo ""
echo "Root after cleanup:"
ls -1 "$ROOT" | wc -l
echo "items at project root"
echo "Done. Review: $ARCHIVE"

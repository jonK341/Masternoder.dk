#!/bin/bash
# Safe orphan / outdated file cleanup on production (/var/www/html).
# Run on server:  cd /var/www/html && sudo bash scripts/server_prune_remote.sh
# Or from local:  python scripts/deploy.py server_prune --ask-pass
set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
cd "$WEB"

echo "=== SERVER PRUNE — $(date -Iseconds) ==="
echo "Web root: $WEB"
df -h / | tail -1
echo

before_avail=$(df --output=avail / | tail -1 | tr -d ' ')

remove_dir() {
  local d="$1"
  if [[ -e "$WEB/$d" ]]; then
    sz=$(du -sh "$WEB/$d" 2>/dev/null | cut -f1 || echo "?")
    echo "  [RM] $d ($sz)"
    rm -rf "$WEB/$d"
  fi
}

echo "--- Dev / backup dirs ---"
for d in removed_scripts_backup server_backup backup_original backups node_modules \
  .cursor mcps .pytest-tmp .pytest_tmp .pytest_cache .firecrawl .vscode; do
  remove_dir "$d"
done
for d in "$WEB"/vidgenerator.backup.*; do
  [[ -e "$d" ]] || continue
  echo "  [RM] $(basename "$d") ($(du -sh "$d" 2>/dev/null | cut -f1))"
  rm -rf "$d"
done

echo "--- Stale shadow modules ---"
for f in src/app.py src/app.pyc vidgenerator/src/app.py vidgenerator/src/app.pyc; do
  [[ -f "$WEB/$f" ]] && echo "  [RM] $f" && rm -f "$WEB/$f"
done
find "$WEB/src" "$WEB/vidgenerator/src" -type f -path '*/__pycache__/app*.pyc' -print -delete 2>/dev/null || true

echo "--- Deploy snapshot files (*.backup.20*) ---"
n=$(find "$WEB" -type f -name '*.backup.20*' 2>/dev/null | wc -l | tr -d ' ')
echo "  Removing $n files"
find "$WEB" -type f -name '*.backup.20*' -delete 2>/dev/null || true

echo "--- Orphan video metadata ---"
for d in "$WEB/videos" "$WEB/vidgenerator/videos"; do
  [[ -d "$d" ]] || continue
  rm -f "$d"/*_temp_audio.mp4 2>/dev/null || true
  shopt -s nullglob
  for f in "$d"/*.job.json "$d"/*.pipeline.json; do
    base="${f%.job.json}"
    base="${base%.pipeline.json}"
    [[ -f "${base}.mp4" ]] || rm -f "$f"
  done
  shopt -u nullglob
done

echo "--- Python cache ---"
find "$WEB" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$WEB" -type f -name '*.pyc' -delete 2>/dev/null || true

if [[ "${1:-}" == "--with-disk" ]]; then
  echo "--- Disk hygiene ---"
  rm -rf /var/cache/nginx/* 2>/dev/null || true
  apt-get clean -y 2>/dev/null || true
  journalctl --vacuum-time=3d 2>/dev/null || true
fi

after_avail=$(df --output=avail / | tail -1 | tr -d ' ')
freed=$((after_avail - before_avail))
echo
echo "=== DONE — freed ~${freed} KB (avail before=$before_avail after=$after_avail) ==="

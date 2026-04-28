#!/bin/bash
# Free disk space on Ubuntu server - run on the server: bash server_free_disk_space.sh
# Safe operations; reports what would be freed. Use --do-it to actually remove.

set -e
DO_IT="${1:-}"

echo "=== Disk usage before ==="
df -h /

echo ""
echo "=== 1. APT: remove unused packages (old kernels, etc.) ==="
if [ "$DO_IT" = "--do-it" ]; then
  sudo apt-get autoremove -y
  echo "Done."
else
  echo "Would run: sudo apt-get autoremove -y"
  sudo apt-get autoremove --dry-run 2>/dev/null || true
fi

echo ""
echo "=== 2. APT: clear package cache ==="
CACHE_SIZE=$(du -sh /var/cache/apt/archives 2>/dev/null | cut -f1)
echo "APT cache size: $CACHE_SIZE"
if [ "$DO_IT" = "--do-it" ]; then
  sudo apt-get clean
  echo "Cleaned."
else
  echo "Would run: sudo apt-get clean"
fi

echo ""
echo "=== 3. Journal logs (keep last 7 days) ==="
if [ "$DO_IT" = "--do-it" ]; then
  sudo journalctl --vacuum-time=7d
else
  echo "Would run: sudo journalctl --vacuum-time=7d"
  journalctl --disk-usage 2>/dev/null || true
fi

echo ""
echo "=== 4. Pip cache (saves space; pip will re-download when needed) ==="
if [ -d "$HOME/.cache/pip" ]; then
  PIP_SIZE=$(du -sh "$HOME/.cache/pip" 2>/dev/null | cut -f1)
  echo "Pip cache size: $PIP_SIZE"
  if [ "$DO_IT" = "--do-it" ]; then
    pip cache purge 2>/dev/null || rm -rf "$HOME/.cache/pip"/*
    echo "Cleaned."
  else
    echo "Would run: pip cache purge (or rm -rf ~/.cache/pip/*)"
  fi
fi

echo ""
echo "=== 5. Old snap revisions (if snap is used) ==="
if command -v snap &>/dev/null; then
  echo "Snap revisions (disabled = old; remove with: sudo snap remove <name> --revision=<rev>):"
  LANG=C snap list --all 2>/dev/null | grep disabled || true
  if [ "$DO_IT" = "--do-it" ]; then
    LANG=C snap list --all 2>/dev/null | awk '/disabled/{print $1, $3}' | while read -r name rev; do
      [ -n "$name" ] && [ -n "$rev" ] && sudo snap remove "$name" --revision="$rev" 2>/dev/null || true
    done
    echo "Done."
  fi
else
  echo "Snap not installed, skipping."
fi

echo ""
echo "=== 6. /var cleanup (unused and cache files) ==="
CURRENT_KERNEL=$(uname -r)

# /var/tmp - old temp files (e.g. 30+ days)
VAR_TMP_SIZE=$(sudo du -sh /var/tmp 2>/dev/null | cut -f1)
echo "/var/tmp size: $VAR_TMP_SIZE (will remove files older than 30 days)"
if [ "$DO_IT" = "--do-it" ]; then
  sudo find /var/tmp -type f -mtime +30 -delete 2>/dev/null || true
  sudo find /var/tmp -type d -empty -delete 2>/dev/null || true
  echo "  Done."
fi

# /var/log - old rotated logs (.gz, .1, .2, etc.)
echo "/var/log: removing rotated logs older than 14 days"
if [ "$DO_IT" = "--do-it" ]; then
  sudo find /var/log -type f \( -name "*.gz" -o -name "*.1" -o -name "*.2" -o -name "*.old" -o -name "*.log.*" \) -mtime +14 -delete 2>/dev/null || true
  echo "  Done."
else
  sudo find /var/log -type f \( -name "*.gz" -o -name "*.1" -o -name "*.2" \) -mtime +14 2>/dev/null | wc -l | xargs -I{} echo "  Would remove {} old log files."
fi

# /var/backups - old .dpkg-old / .dpkg-dist (config backups from package upgrades)
VAR_BACKUP_SIZE=$(sudo du -sh /var/backups 2>/dev/null | cut -f1)
echo "/var/backups size: $VAR_BACKUP_SIZE (will remove .dpkg-old/.dpkg-dist older than 60 days)"
if [ "$DO_IT" = "--do-it" ]; then
  sudo find /var/backups -maxdepth 1 -type f \( -name "*.dpkg-old" -o -name "*.dpkg-dist" \) -mtime +60 -delete 2>/dev/null || true
  echo "  Done."
fi

# /var/lib/apt/lists - partial download dirs (safe; apt update repopulates)
if [ -d /var/lib/apt/lists ]; then
  PARTIAL_COUNT=$(sudo find /var/lib/apt/lists -type d -name "*_partial*" 2>/dev/null | wc -l)
  echo "/var/lib/apt/lists: $PARTIAL_COUNT partial dirs (removing)"
  if [ "$DO_IT" = "--do-it" ]; then
    sudo rm -rf /var/lib/apt/lists/*_partial* 2>/dev/null || true
    echo "  Done."
  fi
fi

echo ""
echo "=== 7. /usr cleanup (unused kernels and optional locale/doc trim) ==="

# /usr/src - old kernel headers (keep only current kernel)
KEEP_HEADERS="linux-headers-$CURRENT_KERNEL"
if [ -d /usr/src ]; then
  echo "/usr/src: removing kernel header dirs other than $KEEP_HEADERS"
  for d in /usr/src/linux-headers-*; do
    [ -d "$d" ] || continue
    [ "$(basename "$d")" = "$KEEP_HEADERS" ] && continue
    if [ "$DO_IT" = "--do-it" ]; then
      echo "  Removing $d"
      sudo rm -rf "$d"
    else
      echo "  Would remove: $d"
    fi
  done
  [ "$DO_IT" = "--do-it" ] && echo "  Done."
fi

# Orphaned package configs (dpkg 'rc' state = removed but config left)
ORPHANED=$(dpkg -l | awk '/^rc / {print $2}')
if [ -n "$ORPHANED" ]; then
  echo "Orphaned package configs (rc): $(echo "$ORPHANED" | wc -l) packages"
  if [ "$DO_IT" = "--do-it" ]; then
    echo "$ORPHANED" | xargs -r sudo dpkg --purge 2>/dev/null || true
    echo "  Purged."
  else
    echo "  Would run: sudo dpkg --purge <packages>"
  fi
fi

# /usr/share/locale - keep only en_US and C (frees often 100–300 MB)
LOCALE_SIZE=$(sudo du -sh /usr/share/locale 2>/dev/null | cut -f1)
echo "/usr/share/locale size: $LOCALE_SIZE (optional: keep only en_US and C)"
if [ "$DO_IT" = "--do-it" ]; then
  if [ -d /usr/share/locale ]; then
    for dir in /usr/share/locale/*/; do
      [ -d "$dir" ] || continue
      dir=$(basename "$dir")
      case "$dir" in
        en_US|en_US*|C|locale) continue ;;
        *) sudo rm -rf "/usr/share/locale/$dir" 2>/dev/null || true ;;
      esac
    done
    echo "  Done (kept en_US, C)."
  fi
fi

# /usr/share/doc - remove compressed docs and PDFs (optional; saves space)
DOC_SIZE=$(sudo du -sh /usr/share/doc 2>/dev/null | cut -f1)
echo "/usr/share/doc size: $DOC_SIZE (optional: remove .gz and .pdf)"
if [ "$DO_IT" = "--do-it" ]; then
  sudo find /usr/share/doc -type f \( -name "*.gz" -o -name "*.pdf" \) -delete 2>/dev/null || true
  echo "  Done."
fi

# /usr/share/man - man pages (saves 50-200 MB; 'man' won't show local docs)
MAN_SIZE=$(sudo du -sh /usr/share/man 2>/dev/null | cut -f1)
echo "/usr/share/man size: $MAN_SIZE (optional: remove to free space)"
if [ "$DO_IT" = "--do-it" ]; then
  sudo rm -rf /usr/share/man/* 2>/dev/null || true
  echo "  Done."
fi

# /usr/share/info - info pages (saves 10-50 MB)
INFO_SIZE=$(sudo du -sh /usr/share/info 2>/dev/null | cut -f1)
echo "/usr/share/info size: $INFO_SIZE (optional: remove)"
if [ "$DO_IT" = "--do-it" ]; then
  sudo rm -rf /usr/share/info/* 2>/dev/null || true
  echo "  Done."
fi

# /usr/share/icons - icon themes (keep hicolor; saves ~100-200 MB on desktop installs)
ICONS_SIZE=$(sudo du -sh /usr/share/icons 2>/dev/null | cut -f1)
echo "/usr/share/icons size: $ICONS_SIZE (optional: keep hicolor only)"
if [ "$DO_IT" = "--do-it" ]; then
  if [ -d /usr/share/icons ]; then
    for d in /usr/share/icons/*/; do
      [ -d "$d" ] || continue
      [ "$(basename "$d")" = "hicolor" ] && continue
      sudo rm -rf "$d" 2>/dev/null || true
    done
    echo "  Done (kept hicolor)."
  fi
fi

# /usr/local/docs - local docs (saves ~50-100 MB; often duplicate of /usr/share/doc)
LOCAL_DOCS_SIZE=$(sudo du -sh /usr/local/docs 2>/dev/null | cut -f1)
echo "/usr/local/docs size: $LOCAL_DOCS_SIZE (optional: remove)"
if [ "$DO_IT" = "--do-it" ]; then
  if [ -d /usr/local/docs ]; then
    sudo rm -rf /usr/local/docs/* 2>/dev/null || true
    echo "  Done."
  fi
fi

# Optional: full /usr/share/doc removal (manual: sudo rm -rf /usr/share/doc/*)
# Frees most of DOC_SIZE; restore with: apt install --reinstall <package>
# Optional: purge -dev packages if you don't compile (can free 500MB+): apt purge $(dpkg -l '*-dev' | awk '/^ii/{print $2}')

echo ""
echo "=== 8. Large directories (top 10 under /) ==="
sudo du -hx --max-depth=1 / 2>/dev/null | sort -hr | head -11

echo ""
if [ "$DO_IT" != "--do-it" ]; then
  echo ">>> Dry run. To actually free space, run: $0 --do-it"
else
  echo "=== Disk usage after ==="
  df -h /
fi

#!/bin/bash
# Remove oldest unused pip packages until ~2-3 GB is freed.
# Prefers orphaned packages, then oldest by install date. Skips packages in requirements.txt.
# Run on server: bash scripts/server_clean_old_unused_pip.sh [--do-it]
# Optional: TARGET_GB=2.5 (default) or set before running.

DO_IT="${1:-}"
TARGET_GB="${TARGET_GB:-2.5}"
# 2.5 GB in bytes (no bc required)
TARGET_BYTES=$(awk "BEGIN {printf \"%.0f\", $TARGET_GB * 1024 * 1024 * 1024}" 2>/dev/null)
[ -z "$TARGET_BYTES" ] && TARGET_BYTES=2684354560

echo "=== Free ~${TARGET_GB} GB by removing oldest (unused) pip packages ==="

# Get site-packages path
SITE=$(python3 -c "import site; print(site.getsitepackages()[0])" 2>/dev/null)
[ -z "$SITE" ] && SITE="/usr/local/lib/python3.10/dist-packages"
[ ! -d "$SITE" ] && SITE="/usr/local/lib/python3.10/site-packages"
[ ! -d "$SITE" ] && echo "Error: site-packages not found" && exit 1
echo "Site-packages: $SITE"

# Packages to never remove (from requirements.txt if present)
REQ_FILE="${REQ_FILE:-/var/www/html/requirements.txt}"
REQUIRED=""
if [ -f "$REQ_FILE" ]; then
  REQUIRED=$(grep -v '^#' "$REQ_FILE" | grep -v '^[[:space:]]*$' | sed 's/\[.*//; s/==.*//; s/>=.*//; s/>.*//; s/<.*//; s/^[[:space:]]*//; s/[[:space:]]*$//' | tr '[:upper:]' '[:lower:]' | sort -u)
fi

# Build list: mtime (epoch) size_bytes name (one line per package, oldest first)
# Scan .dist-info dirs for Name, size of dist-info + code dir, mtime
LIST=$(mktemp)
REMOVE_LIST=$(mktemp)
trap "rm -f $LIST $REMOVE_LIST" EXIT

for distinfo in "$SITE"/*.dist-info; do
  [ -d "$distinfo" ] || continue
  name=$(grep -i "^Name: " "$distinfo/METADATA" 2>/dev/null | head -1 | sed 's/Name: *//; s/[[:space:]]*$//')
  [ -z "$name" ] && continue
  name_lower=$(echo "$name" | tr '[:upper:]' '[:lower:]')
  echo "$REQUIRED" | grep -qFx "$name_lower" && continue
  size=$(du -sb "$distinfo" 2>/dev/null | cut -f1)
  code_name="${name//-/_}"
  for d in "$SITE/$name" "$SITE/$code_name"; do
    [ -d "$d" ] && size=$((size + $(du -sb "$d" 2>/dev/null | cut -f1)))
  done
  mtime=$(stat -c %Y "$distinfo" 2>/dev/null)
  [ -n "$mtime" ] && [ -n "$size" ] && echo "$mtime $size $name"
done > "$LIST"

# Sort by mtime (oldest first), then by size desc (biggest first when same age)
sort -n -k1,1 -k2,2rn "$LIST" > "${LIST}.s" 2>/dev/null || sort -n "$LIST" > "${LIST}.s"
mv "${LIST}.s" "$LIST"

# Prefer orphaned if pip-autoremove available
if pip show pip-autoremove &>/dev/null; then
  ORPHANED=$(pip-autoremove -l 2>/dev/null | grep -v "^#" | sed 's/[[:space:]]*(.*//; s/^[[:space:]]*//; s/[[:space:]]*$//' | tr '[:upper:]' '[:lower:]' | grep -v '^$')
  # Reorder LIST: orphaned first (by age), then rest (by age)
  ORPH_LIST=$(mktemp)
  REST_LIST=$(mktemp)
  while read -r mtime size name; do
    name_lower=$(echo "$name" | tr '[:upper:]' '[:lower:]')
    if echo "$ORPHANED" | grep -qFx "$name_lower"; then
      echo "$mtime $size $name" >> "$ORPH_LIST"
    else
      echo "$mtime $size $name" >> "$REST_LIST"
    fi
  done < "$LIST"
  sort -n -k1 -k2rn "$ORPH_LIST" "$REST_LIST" > "$LIST" 2>/dev/null
  rm -f "$ORPH_LIST" "$REST_LIST"
fi

# Select packages to remove until we reach TARGET_BYTES
FREED=0
TO_REMOVE=""
while read -r mtime size name; do
  [ "$FREED" -ge "$TARGET_BYTES" ] && break
  echo "$name" >> "$REMOVE_LIST"
  TO_REMOVE="$TO_REMOVE $name"
  FREED=$((FREED + size))
done < "$LIST"

# Dedupe
TO_REMOVE=$(sort -u "$REMOVE_LIST" | tr '\n' ' ')
FREED_GB=$(awk "BEGIN {printf \"%.2f\", $FREED/1024/1024/1024}")

if [ -z "$TO_REMOVE" ]; then
  echo "No candidate packages to remove (or all are in requirements.txt)."
  exit 0
fi

echo "Packages to remove (oldest first, until ~${TARGET_GB} GB):"
for pkg in $TO_REMOVE; do echo "  $pkg"; done
echo "Approx total to free: ${FREED_GB} GB"
echo ""

if [ "$DO_IT" = "--do-it" ]; then
  echo "Uninstalling..."
  for pkg in $TO_REMOVE; do
    pip uninstall -y "$pkg" 2>/dev/null || true
  done
  echo "Done."
else
  echo "Dry run. To remove: $0 --do-it"
  echo "Or set target: TARGET_GB=3 $0 --do-it"
fi

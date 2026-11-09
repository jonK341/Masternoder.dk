#!/bin/bash
# Check /usr/local and remove unused/orphaned pip packages. Run on server: bash scripts/server_clean_usr_local.sh
# Use --do-it to actually remove; otherwise only reports.

DO_IT="${1:-}"

echo "=== /usr/local size ==="
du -sh /usr/local 2>/dev/null
echo ""
echo "=== /usr/local breakdown ==="
du -hx --max-depth=1 /usr/local 2>/dev/null | sort -hr | head -15

echo ""
echo "=== Python site-packages (pip) size ==="
for d in /usr/local/lib/python*/dist-packages /usr/local/lib/python*/site-packages; do
  [ -d "$d" ] || continue
  echo -n "$d: "
  du -sh "$d" 2>/dev/null | cut -f1
done

echo ""
echo "=== Pip: installed package count ==="
pip list 2>/dev/null | wc -l

echo ""
echo "=== Remove orphaned pip packages (no longer needed by any top-level package) ==="
if ! pip show pip-autoremove &>/dev/null; then
  echo "Installing pip-autoremove..."
  pip install --no-cache-dir pip-autoremove 2>/dev/null || true
fi
if pip show pip-autoremove &>/dev/null; then
  echo "Orphaned packages (can be removed):"
  pip-autoremove -l 2>/dev/null || true
  if [ "$DO_IT" = "--do-it" ]; then
    echo "Removing orphaned packages..."
    pip-autoremove -y 2>/dev/null || true
    echo "Done."
  else
    echo "Dry run. To remove: $0 --do-it"
  fi
else
  echo "pip-autoremove not available. Pip cache purge only."
fi

echo ""
echo "=== Pip cache purge ==="
if [ "$DO_IT" = "--do-it" ]; then
  pip cache purge 2>/dev/null && echo "Done." || true
else
  echo "Would run: pip cache purge (use --do-it)"
fi

echo ""
echo "=== /usr/local after ==="
du -sh /usr/local 2>/dev/null

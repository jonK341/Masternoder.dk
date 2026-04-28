#!/bin/bash
# Find which disk pip uses for downloads and which partition is full.
# Run on server: bash scripts/server_where_pip_writes.sh

echo "=== All mounted filesystems (look for 100% or high Use%) ==="
df -h

echo ""
echo "=== Where pip/Python write temp files (downloads) ==="
python3 -c "import tempfile; print('TMPDIR/tempdir:', tempfile.gettempdir())" 2>/dev/null
echo "TMPDIR env: ${TMPDIR:-<not set, so /tmp or /var/tmp>}"

echo ""
echo "=== Disk usage for common pip write locations ==="
for d in /tmp /var/tmp /root/.cache/pip /usr/local; do
  [ -d "$d" ] && echo -n "$d: " && df -h "$d" | tail -1 | awk '{print $4 " free on " $6 " (" $5 " used)"}'
done

echo ""
echo "=== Which partition has pip download? ==="
TMPDIR_DEFAULT=$(python3 -c "import tempfile; print(tempfile.gettempdir())" 2>/dev/null)
echo "Pip uses: $TMPDIR_DEFAULT (check 'df -h $TMPDIR_DEFAULT' above)"
echo ""
echo "=== Recommendation ==="
FULL=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
echo "Root (/) is ${FULL}% used. Pip downloads write to /tmp (same as / unless /tmp is a separate mount)."
echo "Free space on the SAME partition as $TMPDIR_DEFAULT, then retry with --no-cache-dir."

#!/bin/bash
# Emergency free space - run when disk is full (e.g. pip failed with "No space left").
# Run on server: bash scripts/server_emergency_free_space.sh
# No set -e so partial failures don't stop the script.

echo "=== Disk before ==="
df -h /

echo ""
echo "=== 1. Pip cache and temp (partial downloads, failed wheels) ==="
pip cache purge 2>/dev/null || true
rm -rf /root/.cache/pip 2>/dev/null || true
rm -rf /tmp/pip-* 2>/dev/null || true
rm -rf /tmp/build 2>/dev/null || true
echo "Done."

echo ""
echo "=== 1b. Playwright browser cache (re-download later if needed) ==="
PLAYWRIGHT_SIZE=$(du -sh /root/.cache/ms-playwright 2>/dev/null | cut -f1 || echo "0")
echo "Playwright cache: ${PLAYWRIGHT_SIZE:-none}"
rm -rf /root/.cache/ms-playwright 2>/dev/null || true
echo "Done."

echo ""
echo "=== 2. APT cache ==="
apt-get clean 2>/dev/null || true
echo "Done."

echo ""
echo "=== 3. Journal (keep 1 day) ==="
journalctl --vacuum-time=1d 2>/dev/null || true
echo "Done."

echo ""
echo "=== 4. /tmp ==="
rm -rf /tmp/pip-* /tmp/tmp* 2>/dev/null || true
find /tmp -type f -mtime +7 -delete 2>/dev/null || true
echo "Done."

echo ""
echo "=== 5. /var/tmp ==="
rm -rf /var/tmp/* 2>/dev/null || true
echo "Done."

echo ""
echo "=== 6. Old rotated logs ==="
find /var/log -type f \( -name "*.gz" -o -name "*.1" -o -name "*.2" -o -name "*.old" \) -delete 2>/dev/null || true
echo "Done."

echo ""
echo "=== 7. Old kernel packages (autoremove) ==="
apt-get autoremove -y 2>/dev/null || true
echo "Done."

echo ""
echo "=== 8. Orphaned dpkg configs ==="
dpkg -l | awk '/^rc / {print $2}' | xargs -r dpkg --purge 2>/dev/null || true
echo "Done."

echo ""
echo "=== Disk after ==="
df -h /

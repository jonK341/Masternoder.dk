#!/bin/bash
# Investigate /usr disk usage - run on server: bash scripts/server_investigate_usr.sh
# Shows what uses space so you can decide what to trim. No deletions.

echo "=== /usr total ==="
du -sh /usr 2>/dev/null

echo ""
echo "=== Top-level /usr (directories by size) ==="
du -hx --max-depth=1 /usr 2>/dev/null | sort -hr | head -15

echo ""
echo "=== Under /usr/share (biggest first) ==="
du -hx --max-depth=1 /usr/share 2>/dev/null | sort -hr | head -20

echo ""
echo "=== Under /usr/local (often pip + man) ==="
du -hx --max-depth=1 /usr/local 2>/dev/null | sort -hr | head -15

echo ""
echo "=== Under /usr/lib (do not delete; info only) ==="
du -hx --max-depth=1 /usr/lib 2>/dev/null | sort -hr | head -12

echo ""
echo "=== Safe-to-trim sizes (approximate) ==="
echo -n "/usr/share/man:    "; du -sh /usr/share/man 2>/dev/null | cut -f1
echo -n "/usr/share/info:  "; du -sh /usr/share/info 2>/dev/null | cut -f1
echo -n "/usr/share/doc:   "; du -sh /usr/share/doc 2>/dev/null | cut -f1
echo -n "/usr/share/locale:"; du -sh /usr/share/locale 2>/dev/null | cut -f1
echo -n "/usr/share/icons: "; du -sh /usr/share/icons 2>/dev/null | cut -f1
echo -n "/usr/src:         "; du -sh /usr/src 2>/dev/null | cut -f1

echo ""
echo "=== Installed -dev packages (removable if you don't compile) ==="
dpkg -l '*-dev' 2>/dev/null | grep '^ii' | wc -l | xargs -I{} echo "Count: {}"
echo "List (first 25):"
dpkg -l '*-dev' 2>/dev/null | grep '^ii' | awk '{print $2}' | head -25

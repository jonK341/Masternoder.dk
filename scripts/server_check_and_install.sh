#!/bin/bash
# Run on the server as root. Checks /var/www/html and installs deps with system Python.
# Usage: bash server_check_and_install.sh   or: cd /var/www/html && bash scripts/server_check_and_install.sh

set -e
HTML=/var/www/html
REQ="$HTML/requirements.txt"

echo "=== Check /var/www/html ==="
ls -la "$HTML" 2>/dev/null || { echo "Missing: $HTML"; exit 1; }
echo ""
echo "=== Check key files ==="
for f in "$HTML/wsgi.py" "$HTML/run.py" "$REQ" "$HTML/vidgenerator/uwsgi.ini"; do
  if [ -f "$f" ]; then echo "  OK  $f"; else echo "  MISS $f"; fi
done
for d in "$HTML/src" "$HTML/backend" "$HTML/vidgenerator"; do
  if [ -d "$d" ]; then echo "  OK  $d/"; else echo "  MISS $d/"; fi
done

if [ ! -f "$REQ" ]; then
  echo ""
  echo "No $REQ — deploy the full project first (e.g. git pull, rsync, or copy run.py + requirements.txt + src/ + backend/ to $HTML)."
  exit 1
fi

echo ""
echo "=== Install deps with system Python (pip3 may be missing; use python3 -m pip) ==="
python3 -m pip install --no-cache-dir -r "$REQ" || true
echo ""
echo "Done. Then start uWSGI: sudo systemctl start uwsgi"
echo "Or run app manually: cd $HTML && python3 run.py   (if run.py exists)"

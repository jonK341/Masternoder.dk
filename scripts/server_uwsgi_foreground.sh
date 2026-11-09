#!/bin/bash
# Run on the server to see the real uwsgi error (run in foreground, then Ctrl+C).
# Usage: bash server_uwsgi_foreground.sh   or: cd /var/www/html && bash scripts/server_uwsgi_foreground.sh

set -e
INI="/var/www/html/vidgenerator/uwsgi.ini"
LOG="/var/www/html/vidgenerator/uwsgi.log"

# Strip CRLF so "invalid user www-data\r" is fixed
if [ -f "$INI" ]; then
  sed -i 's/\r$//' "$INI"
  echo "[OK] Stripped CRLF from $INI"
fi

# Prefer venv in vidgenerator if it exists
if [ -d /var/www/html/vidgenerator/.venv/bin ]; then
  UWSGI="/var/www/html/vidgenerator/.venv/bin/uwsgi"
elif [ -d /var/www/html/.venv/bin ]; then
  UWSGI="/var/www/html/.venv/bin/uwsgi"
else
  UWSGI="/usr/bin/uwsgi"
fi
echo "[OK] Using $UWSGI"

echo ""
echo "Starting uwsgi in foreground (first 60 lines of output; Ctrl+C to stop)..."
echo "=============================================="
sudo -u www-data "$UWSGI" --ini "$INI" 2>&1 | head -60

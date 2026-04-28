#!/bin/bash
# Run on the server as root: bash server_fix_uwsgi.sh
# Fix 502: free port 5000, then stop uwsgi, fix perms, start uwsgi. (Gunicorn removed from project.)

set -e
echo "=== 1. Free port 5000 (stop anything listening) ==="
systemctl stop vidgenerator-gunicorn 2>/dev/null || true
pkill -f gunicorn 2>/dev/null || true
sleep 1
if command -v fuser &>/dev/null; then
  fuser -k 5000/tcp 2>/dev/null || true
else
  (ss -tlnp | grep -q ':5000 ') && kill $(ss -tlnp | grep ':5000 ' | sed -n 's/.*pid=\([0-9]*\).*/\1/p') 2>/dev/null || true
fi
sleep 1
echo "Port 5000: $(ss -tlnp | grep 5000 || echo 'free')"

echo ""
echo "=== 2. Stop uwsgi ==="
systemctl stop uwsgi 2>/dev/null || true
pkill -f uwsgi 2>/dev/null || true
sleep 2
if command -v fuser &>/dev/null; then
  fuser -k 5000/tcp 2>/dev/null || true
fi
sleep 1
echo "Port 5000: $(ss -tlnp | grep 5000 || echo 'free')"

echo ""
echo "=== 2b. Use system Python (avoid broken venv: encodings missing) ==="
sed -i 's/^virtualenv = /#virtualenv = /' /var/www/html/vidgenerator/uwsgi.ini 2>/dev/null || true
echo "  (Commented virtualenv in uwsgi.ini; uwsgi will use system Python)"
echo "  If imports fail, install deps: python3 -m pip install -r /var/www/html/requirements.txt"
echo ""
echo "=== 3. Permissions so www-data can chdir and write log ==="
chmod 755 /var/www /var/www/html /var/www/html/vidgenerator 2>/dev/null || true
touch /var/www/html/vidgenerator/uwsgi.log 2>/dev/null || true
chown www-data:www-data /var/www/html/vidgenerator/uwsgi.log 2>/dev/null || true
chmod 644 /var/www/html/vidgenerator/uwsgi.log 2>/dev/null || true
ls -la /var/www/html/vidgenerator/uwsgi.ini /var/www/html/vidgenerator/uwsgi.log 2>/dev/null || true

echo ""
echo "=== 4. Run uwsgi in foreground (see real error; Ctrl+C to stop) ==="
cd /var/www/html/vidgenerator
sudo -u www-data /usr/bin/uwsgi --ini /var/www/html/vidgenerator/uwsgi.ini 2>&1 || true

echo ""
echo "If uwsgi started above (no immediate exit), run in another terminal: sudo systemctl start uwsgi"

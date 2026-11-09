#!/bin/bash
#
# Production Apply Routes - run ON the server to apply route/blueprint updates.
# Use after: deploy, git pull, rsync, or any file sync that updates backend/.
#
# Usage (on server):
#   cd /var/www/html && bash scripts/production_apply_routes.sh
#
# Or via SSH from local:
#   ssh root@masternoder.dk "cd /var/www/html && bash scripts/production_apply_routes.sh"
#
# Register Intelligence auto-discovers blueprints at app startup; this script
# ensures PYTHONPATH, clears cache, and restarts services so new routes load.
#
REMOTE_BASE="${REMOTE_BASE:-/var/www/html}"
cd "$REMOTE_BASE" || exit 1

PY="python3"
if [[ -x "$REMOTE_BASE/.venv/bin/python" ]]; then
  PY="$REMOTE_BASE/.venv/bin/python"
fi

echo "=========================================="
echo "PRODUCTION APPLY ROUTES"
echo "=========================================="
echo "[0/7] Database migrations (idempotent)..."
if [[ -f "$REMOTE_BASE/scripts/apply_db_migrations.py" ]]; then
  if ! "$PY" "$REMOTE_BASE/scripts/apply_db_migrations.py"; then
    echo "  [WARN] DB migrations failed — continuing with route reload (check logs)"
  fi
else
  echo "  skipped (apply_db_migrations.py not present yet)"
fi
echo "  done"

echo "[1/7] Clearing Python cache..."
find "$REMOTE_BASE" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$REMOTE_BASE" -name '*.pyc' -delete 2>/dev/null || true
echo "  done"

echo "[2/7] Purging nginx cache..."
rm -rf /var/cache/nginx/* 2>/dev/null || true
echo "  done"

echo "[3/7] Ensuring uwsgi pythonpath..."
for cfg in /etc/uwsgi/apps-enabled/vidgenerator.ini /etc/uwsgi/apps-available/vidgenerator.ini "$REMOTE_BASE/vidgenerator/uwsgi.ini"; do
    if [ -f "$cfg" ]; then
        if ! grep -q "pythonpath = $REMOTE_BASE" "$cfg" 2>/dev/null; then
            sed -i.bak "s|pythonpath = .*|pythonpath = $REMOTE_BASE|" "$cfg" 2>/dev/null || true
            echo "  Updated $cfg"
        fi
        break
    fi
done

echo "[4/7] Ensuring python-proxy PYTHONPATH..."
mkdir -p /etc/systemd/system/python-proxy.service.d
cat > /etc/systemd/system/python-proxy.service.d/environment.conf << EOF
[Service]
Environment="PYTHONPATH=$REMOTE_BASE"
EOF
systemctl daemon-reload 2>/dev/null || true
echo "  done"

echo "[5/7] Restarting services (order: python-proxy -> uwsgi-vidgenerator -> uwsgi -> nginx)..."
systemctl restart python-proxy 2>/dev/null || systemctl restart python-proxy.service 2>/dev/null || true
sleep 4
systemctl stop uwsgi-vidgenerator 2>/dev/null || true
sleep 2
systemctl start uwsgi-vidgenerator 2>/dev/null || true
sleep 5
systemctl restart uwsgi 2>/dev/null || true
sleep 2
systemctl reload nginx 2>/dev/null || systemctl restart nginx 2>/dev/null || true
echo "  done"

echo "[6/7] Quick route check..."
for path in /api/version /api/generator/test /api/unified/status; do
    code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:5000$path" 2>/dev/null || echo "---")
    echo "  $path: $code"
done

echo "=========================================="
echo "APPLY ROUTES COMPLETE"
echo "=========================================="

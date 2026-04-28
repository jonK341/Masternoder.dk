"""Fix 502 by creating uwsgi apps-enabled symlink and restarting.

Run this from your LOCAL machine (Windows/Mac/Linux), not on the server.
It SSHs to masternoder.dk and does: stop services, fix perms, install
uwsgi-vidgenerator.service, start it. On the server, use instead:
  sudo systemctl restart uwsgi-vidgenerator
"""
import base64
import json
import os
import paramiko
import subprocess
import sys
import time

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

SERVER_HOST = deploy_host()
SERVER_USER = deploy_user()
SERVER_PASS = require_deploy_pass()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

def run(cmd, label='', timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    try:
        out = stdout.read().decode(errors="replace").strip()
        err = stderr.read().decode(errors="replace").strip()
    except Exception:
        out, err = "", ""
    if label:
        print(f'[{label}]')
    if out:
        print(out)
    if err:
        print('STDERR:', err)
    return out

# Step 1: Clear listen queue (201/200) and free port 5000 – stop uWSGI so kernel drops queued connections, then kill stragglers
print('=== STEP 1: Clear listen queue & free port 5000 (stop uWSGI → queue reset, then kill stragglers) ===')
print('  (Stopping uWSGI drops the socket and deletes all queued connections e.g. 201/200.)')
run('systemctl stop uwsgi-vidgenerator 2>/dev/null || true', 'stop uwsgi-vidgenerator')
run('systemctl stop uwsgi 2>/dev/null || true', 'stop uwsgi')
run('systemctl disable uwsgi 2>/dev/null || true', 'disable LSB uwsgi (prevents boot conflict)')
run('systemctl stop python-proxy 2>/dev/null || true', 'stop python-proxy')
run('systemctl disable python-proxy 2>/dev/null || true', 'disable python-proxy (keep inactive)')
run('systemctl stop vidgenerator-gunicorn 2>/dev/null || true', 'stop vidgenerator-gunicorn')
time.sleep(2)
# Kill any remaining uwsgi/gunicorn so no process holds the socket (queue is then gone)
run('pkill -9 -f uwsgi 2>/dev/null || true', 'kill uwsgi (SIGKILL)')
run('pkill -9 -f start-stop-daemon 2>/dev/null || true', 'kill start-stop-daemon')
run('pkill -9 -f gunicorn 2>/dev/null || true', 'kill gunicorn')
time.sleep(3)
run('fuser -k 5000/tcp 2>/dev/null || true', 'fuser 5000')
run('fuser -k 5003/tcp 2>/dev/null || true', 'fuser 5003')
time.sleep(2)
# Second round: orphan processes may have been respawned; ensure queue/port fully released
run('pkill -9 -f uwsgi 2>/dev/null || true', 'kill uwsgi again')
run('pkill -9 -f start-stop-daemon 2>/dev/null || true', 'kill start-stop-daemon again')
run('fuser -k 5000/tcp 2>/dev/null || true', 'fuser 5000 again')
time.sleep(2)
run('ss -tlnp 2>/dev/null | grep -E ":5000 |:5003 " || true', 'check 5000/5003')
out = run('ss -tlnp 2>/dev/null | grep ":5000 " || true')
if out.strip():
    run('fuser -k 5000/tcp 2>/dev/null || true')
    time.sleep(2)

# Step 1b: Fix chdir permission (www-data must be able to chdir to /var/www/html)
# uWSGI drops to uid=www-data then chdirs; if www-data does not own or have traverse, chdir fails.
print('\n=== STEP 1b: Permissions so www-data can chdir and write log ===')
run('chmod 755 /var /var/www /var/www/html /var/www/html/vidgenerator 2>/dev/null || true', 'chmod path')
run('chown -R www-data:www-data /var/www/html 2>/dev/null || true', 'chown app dir to www-data (fixes chdir)')
run('touch /var/www/html/uwsgi.log 2>/dev/null; chown www-data:www-data /var/www/html/uwsgi.log 2>/dev/null || true', 'log file')
run('chmod 644 /var/www/html/uwsgi.log 2>/dev/null || true', 'log perms')
run('mkdir -p /var/www/html/instance 2>/dev/null; chmod 775 /var/www/html/instance 2>/dev/null; chown www-data:www-data /var/www/html/instance 2>/dev/null || true', 'instance dir for SQLite')
run('touch /var/www/html/instance/database.db 2>/dev/null; chown www-data:www-data /var/www/html/instance/database.db 2>/dev/null; chmod 664 /var/www/html/instance/database.db 2>/dev/null || true', 'instance/database.db writable by www-data (fixes "unable to open database file")')

# Step 2: Ensure apps-enabled has ONLY vidgenerator.ini (Debian emperor starts one vassal per file; README = second "config" = second bind to 5000 = "Address already in use")
print('\n=== STEP 2: Create symlink (only one app in apps-enabled) ===')
run('mkdir -p /etc/uwsgi/apps-enabled', 'ensure dir exists')
run('rm -f /etc/uwsgi/apps-enabled/README /etc/uwsgi/apps-enabled/README.* 2>/dev/null || true', 'remove README')
run('ln -sf /var/www/html/uwsgi.ini /etc/uwsgi/apps-enabled/vidgenerator.ini', 'create symlink')
out = run('ls -la /etc/uwsgi/apps-enabled/', 'verify symlink')
print(out)

# Step 2b: Ensure listen queue >= 200 (avoids "listen queue full (101/100)" and nginx 110/timeouts during startup)
run('grep -q "^listen = " /var/www/html/uwsgi.ini 2>/dev/null || sed -i "/http-socket = 127.0.0.1:5000/a listen = 200" /var/www/html/uwsgi.ini', 'listen queue size')
run('grep -E "listen|http-socket" /var/www/html/uwsgi.ini 2>/dev/null || true', 'verify listen')
# Step 2c: Strip Windows CRLF from uwsgi.ini (fix "invalid user 'www-data\\r'" on Linux)
print('\n=== STEP 2c: Fix line endings in uwsgi.ini ===')
run('sed -i "s/\\r$//" /var/www/html/uwsgi.ini 2>/dev/null || true', 'strip CRLF')
run('grep -E "uid|gid" /var/www/html/uwsgi.ini | cat -A 2>/dev/null || true', 'verify no \\r')

# Step 2d: Comment out virtualenv so uwsgi uses system Python (server venv often broken: encodings missing)
print('\n=== STEP 2d: Use system Python (avoid broken venv) ===')
run("sed -i 's/^virtualenv = /#virtualenv = /' /var/www/html/uwsgi.ini 2>/dev/null || true", 'comment virtualenv')
print('  (uwsgi will use system Python; if venv was broken with "No module named encodings", this fixes it)')

# Clear uwsgi logs so Step 6 shows only this run
run('true > /var/www/html/vidgenerator/uwsgi.log 2>/dev/null; true > /var/log/uwsgi/app/vidgenerator.log 2>/dev/null || true', 'clear uwsgi logs')
# Ensure only .ini in apps-enabled (emperor starts one vassal per file; README = extra "config" = duplicate bind)
run('find /etc/uwsgi/apps-enabled -maxdepth 1 -type f ! -name "*.ini" -delete 2>/dev/null || true')

# Step 2e: Install direct systemd unit (bypass LSB init script that fails with "...fail!")
# uwsgi-vidgenerator has no separate ini: it uses /var/www/html/uwsgi.ini only (no uwsgi-vidgenerator.ini).
print('\n=== STEP 2e: Install uwsgi-vidgenerator.service (direct unit, no LSB) ===')
_unit_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'systemd', 'uwsgi-vidgenerator.service')
if os.path.isfile(_unit_path):
    with open(_unit_path, 'r', encoding='utf-8') as _f:
        unit_content = _f.read()
else:
    raise FileNotFoundError(f"Unit file not found: {_unit_path}")
b64 = base64.b64encode(unit_content.encode()).decode()
run(f"echo '{b64}' | base64 -d > /etc/systemd/system/uwsgi-vidgenerator.service", 'write unit', timeout=10)
run('systemctl daemon-reload', 'daemon-reload', timeout=10)
run('systemctl enable uwsgi-vidgenerator 2>/dev/null || true', 'enable unit', timeout=5)

# Step 2e2: Install second backend (port 5001) for load spreading
_unit_5001 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'systemd', 'uwsgi-vidgenerator-5001.service')
if os.path.isfile(_unit_5001):
    print('\n=== STEP 2e2: Install uwsgi-vidgenerator-5001.service (second backend on 5001) ===')
    with open(_unit_5001, 'r', encoding='utf-8') as _f:
        _c5001 = _f.read()
    _b64_5001 = base64.b64encode(_c5001.encode()).decode()
    run(f"echo '{_b64_5001}' | base64 -d > /etc/systemd/system/uwsgi-vidgenerator-5001.service", 'write 5001 unit', timeout=10)
    run('systemctl daemon-reload', 'daemon-reload', timeout=10)
    run('systemctl enable uwsgi-vidgenerator-5001 2>/dev/null || true', 'enable 5001', timeout=5)
else:
    print('\n  [SKIP] uwsgi-vidgenerator-5001.service not found (optional second backend)')

# Step 2f: Fix nginx "conflicting server name masternoder.dk" (disables duplicate configs so reload has no warnings)
_root = os.path.dirname(os.path.abspath(__file__))
_nginx_conflict = os.path.join(_root, 'scripts', 'fix_nginx_conflicting_server_name.py')
if os.path.isfile(_nginx_conflict):
    print('\n=== STEP 2f: Fix nginx conflicting server name (masternoder.dk / www) ===')
    r = subprocess.run([sys.executable, _nginx_conflict], cwd=_root, timeout=45)
    if r.returncode != 0:
        print('  [WARN] fix_nginx_conflicting_server_name.py exited with', r.returncode)
    run('nginx -t 2>&1 || true', 'nginx -t')
    # Reload so single config is active (script may have removed duplicates)
    run('systemctl reload nginx 2>&1 || true', 'reload nginx (apply single config)')

# Step 3: Reset listen queue and port 5000, then start uwsgi-vidgenerator
print('\n=== STEP 3: Reset listen queue & port 5000, then start uwsgi-vidgenerator ===')
run('systemctl stop uwsgi-vidgenerator 2>/dev/null || true', 'stop uwsgi-vidgenerator (clean)')
time.sleep(2)
run('pkill -9 -f uwsgi 2>/dev/null || true; fuser -k 5000/tcp 2>/dev/null || true', 'clear queue & free 5000')
time.sleep(2)
run('ss -tlnp 2>/dev/null | grep ":5000 " || echo "Port 5000 free"', 'verify 5000 free')
time.sleep(1)
run('systemctl start uwsgi-vidgenerator', 'start uwsgi-vidgenerator', timeout=25)
status = run('systemctl is-active uwsgi-vidgenerator 2>/dev/null || true')
if 'active' not in status:
    print('  [WARN] uwsgi-vidgenerator did not start. Showing why:')
    print('  --- systemctl status uwsgi-vidgenerator ---')
    print(run('systemctl status uwsgi-vidgenerator 2>&1 || true', timeout=10))
    print('  --- journalctl -u uwsgi-vidgenerator -n 35 ---')
    print(run('journalctl -u uwsgi-vidgenerator -n 35 --no-pager 2>/dev/null || true', timeout=10))
    print('  --- Trying uwsgi directly (daemon) so app runs despite service failure ---')
    run('sudo -u www-data /usr/bin/uwsgi --ini /var/www/html/uwsgi.ini --daemonize /var/www/html/uwsgi.log 2>&1 || true', 'uwsgi daemon', timeout=15)
    time.sleep(3)
    status = run('systemctl is-active uwsgi-vidgenerator 2>/dev/null || true')
    if 'active' not in status:
        out = run('ss -tlnp 2>/dev/null | grep 5000 || true')
        if out.strip():
            print('  [OK] Port 5000 is in use (uwsgi started via daemon fallback).')
        else:
            print('  [WARN] uwsgi still not running. Running in foreground to capture error:')
            err = run('timeout 6 sudo -u www-data /usr/bin/uwsgi --ini /var/www/html/uwsgi.ini 2>&1 || true', 'uwsgi foreground (6s)', timeout=12)
            if err:
                for line in err.splitlines()[:30]:
                    print('   ', line)
# We use only uwsgi-vidgenerator (direct unit); no emperor. See docs/DEPLOYMENT_PLAN.md.
# With lazy-apps=false, workers load 126 blueprints – can take 60–90s. Poll until :5000 responds (30s curl, short loop).
print('Waiting for workers to finish loading (polling :5000 every 15s, 30s curl timeout, up to ~2.5 min)...')
port_code = ''
for attempt in range(10):  # 30s + 9*15s = ~2.5 min max; 30s per curl
    time.sleep(30 if attempt == 0 else 15)
    out = run('curl -s -m 30 -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/ 2>/dev/null || true', timeout=32)
    port_code = (out or '').strip()
    if port_code and port_code != '000':
        print(f'  Port 5000 responded after ~{30 + attempt * 15}s: HTTP {port_code}')
        break
    print(f'  Attempt {attempt + 1}/10: no response yet (workers may still be loading)')
if not port_code or port_code == '000':
    port_code = '000'
    print('  Port 5000: still no response after ~2.5 min – see Step 6 / 6b (or workers killed by OOM; try processes=2 in uwsgi.ini).')

# Step 3b: Start second backend on 5001 (load spreading)
run('fuser -k 5001/tcp 2>/dev/null || true', 'free 5001')
time.sleep(1)
run('systemctl start uwsgi-vidgenerator-5001 2>/dev/null || true', 'start uwsgi-vidgenerator-5001', timeout=20)

# Step 4: Verify
print('\n=== STEP 4: Verify ===')
for svc in ['uwsgi-vidgenerator', 'uwsgi-vidgenerator-5001', 'uwsgi', 'python-proxy', 'nginx']:
    st = run(f'systemctl is-active {svc} 2>/dev/null || echo inactive')
    print(f'  {svc}: {st.strip() or "inactive"}')
print('Processes:', run('ps aux | grep uwsgi | grep -v grep'))
print('Port 5000:', run('ss -tlnp | grep 5000'))

# Step 4b: Reload nginx once app is up so it reconnects to :5000 (avoids connect() failed 111 / recv 104)
if port_code and port_code != '000':
    run('systemctl reload nginx 2>&1 || true', 'reload nginx (reconnect to :5000)')

# Step 5: Test HTTP (we already have port_code from above) and HTTPS
print('\n=== STEP 5: Test HTTP ===')
if port_code and port_code != '000':
    print(f'  Port 5000: HTTP {port_code}')
else:
    print('  Port 5000: no response (000/timeout) – workers may have crashed; see Step 6 / 6b.')
    print('  If "remains running" appeared before: run  python scripts/reset_port_5000.py   then  python fix_502.py  again.')
out = run('curl -s -m 30 -o /dev/null -w "%{http_code}" https://masternoder.dk/ 2>/dev/null || true', timeout=32)
code = (out or '').strip()
if code and code != '000':
    print(f'  HTTPS site (root): HTTP {code}')
else:
    print('  HTTPS site: no response (000/timeout)')

# Step 5b: If port 5000 is 200 but HTTPS is not, fix nginx (proxy + timeouts) and re-test
if (port_code == '200') and (not code or code == '000' or code == '502' or code == '504'):
    print('\n=== STEP 5b: Fix nginx (proxy to 5000 + timeouts) then re-test HTTPS ===')
    root = os.path.dirname(os.path.abspath(__file__))
    for script in ['scripts/fix_nginx_proxy_all_pages.py', 'scripts/fix_504_timeouts.py']:
        path = os.path.join(root, script)
        if os.path.isfile(path):
            print(f'  Running {script}...')
            r = subprocess.run([sys.executable, path], cwd=root, timeout=60)
            if r.returncode != 0:
                print(f'  [WARN] {script} exited with {r.returncode}')
    out2 = run('curl -s -m 30 -o /dev/null -w "%{http_code}" https://masternoder.dk/ 2>/dev/null || true', timeout=32)
    code2 = (out2 or '').strip()
    if code2 and code2 == '200':
        print(f'  HTTPS after nginx fix: HTTP {code2}')
    else:
        print(f'  HTTPS after nginx fix: {code2 or "000"} (if still 502, check nginx error.log and server_name)')

# Step 5c: If app responded on port 5000, run URL timing and refresh logs/url_timing_results.json
if port_code and port_code != '000':
    _root = os.path.dirname(os.path.abspath(__file__))
    _timing_script = os.path.join(_root, 'scripts', 'test_url_timing.py')
    _results_path = os.path.join(_root, 'logs', 'url_timing_results.json')
    if os.path.isfile(_timing_script):
        print('\n=== STEP 5c: URL timing (refresh results) ===')
        r = subprocess.run([sys.executable, _timing_script], cwd=_root, timeout=600)
        if r.returncode != 0:
            print(f'  [WARN] test_url_timing.py exited with {r.returncode}')
        elif os.path.isfile(_results_path):
            print('  Results written to logs/url_timing_results.json')

# Step 6: Show log (daemon log first; then project uwsgi.log; then journalctl)
print('\n=== STEP 6: Recent uwsgi log (this run) ===')
out = run('tail -60 /var/log/uwsgi/app/vidgenerator.log 2>/dev/null')
if out:
    print(out)
else:
    out = run('tail -60 /var/www/html/uwsgi.log 2>/dev/null')
    if out:
        print(out)
if not out:
    out = run('journalctl -u uwsgi-vidgenerator -n 25 --no-pager 2>/dev/null || true')
    if out:
        print(out)
    else:
        print('  (no log)')

# Step 6b: If port 5000 returned 000, show daemon log and test app load (to see Python/import errors)
if port_code == '000' or not port_code:
    print('\n=== STEP 6b: Diagnose why workers do not respond (daemon log + app load test) ===')
    run('echo "--- /var/log/uwsgi/app/vidgenerator.log ---"; cat /var/log/uwsgi/app/vidgenerator.log 2>/dev/null || true')
    run('echo "--- /var/www/html/uwsgi.log ---"; cat /var/www/html/uwsgi.log 2>/dev/null || true')
    print('  App load test (Python import, max 45s):')
    try:
        app_test = run('cd /var/www/html && sudo -u www-data timeout 30 python3 -c "from src.app import create_app; create_app(); print(\"OK\")" 2>&1', timeout=32)
        for line in (app_test or '').splitlines():
            print('   ', line)
    except BaseException as e:
        print('   ', '(timeout or interrupt:', type(e).__name__, str(e)[:50], ')')

ssh.close()

# Show URL timing results summary (from logs/url_timing_results.json)
_results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'url_timing_results.json')
if os.path.isfile(_results_path):
    try:
        with open(_results_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        results = data.get('results') or []
        total_sec = data.get('total_sec')
        ok_count = sum(1 for r in results if r.get('ok'))
        fail_count = len(results) - ok_count
        print('\n=== URL timing results (logs/url_timing_results.json) ===')
        print(f'  Endpoints: {ok_count} OK, {fail_count} failed (total {len(results)})')
        if total_sec is not None:
            print(f'  Total time: {total_sec:.1f}s')
        if fail_count > 0:
            failed = [r for r in results if not r.get('ok')]
            print('  Failed/timeout:', ', '.join(r.get('name', r.get('path', '?')) for r in failed[:8]))
            if len(failed) > 8:
                print(f'  ... and {len(failed) - 8} more')
    except (json.JSONDecodeError, OSError) as e:
        print('\n  (Could not read url_timing_results.json:', str(e)[:60], ')')

print('\nDone.')
print('  URL timing: python scripts/test_url_timing.py  →  logs/url_timing_results.json')

import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=20)

def run(cmd, t=30):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode('utf-8', errors='replace').strip(), err.read().decode('utf-8', errors='replace').strip()

# Check Python syntax of the uploaded file
o, e = run("python3 -m py_compile /var/www/html/backend/routes/missing_endpoints_routes.py 2>&1 && echo 'SYNTAX OK' || echo 'SYNTAX ERROR'")
print("Syntax check:", o, e)
print()

# Check for any app startup errors
o, e = run("journalctl -u uwsgi -n 100 2>/dev/null | grep -E 'error|Error|ERROR|Traceback|Exception|Warning|failed|FAILED' | tail -30")
print("Recent uWSGI errors:")
print(o or "(none)")
print()

# Test direct import
o, e = run("""python3 -c "
import sys
sys.path.insert(0, '/var/www/html')
try:
    import backend.routes.missing_endpoints_routes as m
    has_ov = hasattr(m, 'system_overview')
    # Count routes on blueprint
    n_routes = len(m.missing_endpoints_bp.deferred_functions)
    print('import OK, has_system_overview:', has_ov, ', deferred_functions:', n_routes)
except Exception as ex:
    print('IMPORT ERROR:', ex)
    import traceback
    traceback.print_exc()
" 2>&1""", t=20)
print("Direct import test:")
print(o or "(empty)")
print()

# Check what the new ROOT missing_endpoints file actually has at lines 3770-3785
o, _ = run("sed -n '3770,3785p' /var/www/html/backend/routes/missing_endpoints_routes.py")
print("ROOT file lines 3770-3785:")
print(o)

import os
ssh.close()

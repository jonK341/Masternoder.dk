import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password='eD)2[K+[S#m_#$3!', timeout=20)

def run(cmd, t=30):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode().strip(), err.read().decode().strip()

# Find ALL missing_endpoints_routes.py on the server
o, _ = run("find /var/www/html -name 'missing_endpoints_routes.py' 2>/dev/null")
print("All missing_endpoints files:", o)

# Check if there's a cached version somewhere
o, _ = run("find /var/www -name 'missing_endpoints_routes*.pyc' 2>/dev/null")
print("Cached .pyc files:", o or "(none)")

# Check how many lines the server file has vs the function name
o, _ = run("grep -c 'def system_overview' /var/www/html/vidgenerator/backend/routes/missing_endpoints_routes.py")
print("system_overview function count:", o)

# Check which file Python actually imports
o, _ = run(r"""python3 -c "
import sys
sys.path.insert(0, '/var/www/html')
import backend.routes.missing_endpoints_routes as m
print('FILE:', m.__file__)
has_route = any('/api/system/overview' == str(r) for r in getattr(m.missing_endpoints_bp, 'deferred_functions', []))
import inspect
src = inspect.getsource(m.system_overview) if hasattr(m, 'system_overview') else 'NOT FOUND'
print('HAS system_overview attr:', hasattr(m, 'system_overview'))
print('system_overview source first 50 chars:', src[:50] if src else 'N/A')
" 2>&1""", t=20)
print("Import check:", o)
ssh.close()

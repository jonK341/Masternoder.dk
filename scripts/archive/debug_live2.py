import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password='eD)2[K+[S#m_#$3!', timeout=30)

def run(cmd, t=30):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode('utf-8', errors='replace').strip(), err.read().decode('utf-8', errors='replace').strip()

# What module file is the LIVE Flask process actually using?
# We can check this via a live request that dumps sys.modules
o, _ = run("curl -s 'http://localhost:5000/api/list-routes' --max-time 8 | python3 -c \"import sys,json; d=json.load(sys.stdin); routes=[r for r in d.get('routes',[]) if 'overview' in r.get('path','')]; print('overview_routes:', routes)\" 2>/dev/null || echo 'no list-routes endpoint'")
print("List routes test:", o)

# Check if the live Flask app has the route via a probe
o, _ = run("""curl -s 'http://localhost:5000/api/debug/routes?filter=overview' --max-time 8 2>/dev/null || curl -s 'http://localhost:5000/vidgenerator/api/debug/routes?filter=overview' --max-time 8 2>/dev/null | head -200""")
print("Debug routes:", o[:300])

# Force uwsgi workers to reload by sending SIGHUP
print("\nSending SIGHUP to uwsgi master to force worker reload...")
o, e = run("kill -HUP $(systemctl show -p MainPID uwsgi | cut -d= -f2) 2>/dev/null && echo 'SIGHUP sent' || systemctl reload uwsgi 2>/dev/null && echo 'reload sent' || echo 'could not reload'")
print("Reload:", o)
time.sleep(8)

# Re-test
o, _ = run("curl -s 'http://localhost:5000/vidgenerator/api/system/overview?compact=1' --max-time 10 -w '\\nSTATUS:%{http_code}'")
print("\nAfter SIGHUP test:", o[:200])

ssh.close()

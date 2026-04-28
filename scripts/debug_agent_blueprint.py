"""Debug why agent_profile blueprint isn't loading."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run(ssh, cmd, timeout=25):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

# Test import directly
print("=== Import test ===")
r = run(ssh, """cd /var/www/html/vidgenerator && python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from backend.routes.agent_profile_routes import agent_profile_bp
    print('Import OK:', agent_profile_bp)
except Exception as e:
    print('Import FAILED:', e)
    import traceback; traceback.print_exc()
" 2>&1""", timeout=25)
print(r)

print("\n=== Check agent_db_service import ===")
r2 = run(ssh, """cd /var/www/html/vidgenerator && python3 -c "
import sys; sys.path.insert(0, '.')
try:
    from backend.services.agent_db_service import agent_db_service
    print('agent_db_service OK')
except Exception as e:
    print('FAILED:', e)
    import traceback; traceback.print_exc()
" 2>&1""", timeout=25)
print(r2)

print("\n=== Check file exists ===")
print(run(ssh, "ls -la /var/www/html/vidgenerator/backend/routes/agent_profile_routes.py /var/www/html/vidgenerator/backend/services/agent_db_service.py 2>&1"))

print("\n=== Recent flask log ===")
print(run(ssh, "tail -20 /var/www/html/vidgenerator/flask_app.log 2>/dev/null || echo 'no log'"))

ssh.close()

"""Fix permissions and test points on production."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
    
    cmds = [
        "chown -R www-data:www-data /var/www/html/logs/",
        "chmod -R 775 /var/www/html/logs/",
        "ls -la /var/www/html/logs/unified_points/",
    ]
    for cmd in cmds:
        print(f">>> {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            print(out)
        if err:
            print(f"  ERR: {err}")
        print()
    
    # Now test add_points as www-data
    test = r'''
import sys, os, json
sys.path.insert(0, "/var/www/html")
os.chdir("/var/www/html")
from backend.services.unified_points_database import unified_points_db
result = unified_points_db.add_points("default_user", "generation_points", 25, source="test_fix")
print(f"Result: {result}")
result2 = unified_points_db.add_points("default_user", "xp_points", 37.5, source="test_fix")
print(f"XP: {result2}")
pts = unified_points_db.get_all_points("default_user")
print(f"All points: {json.dumps(pts, indent=2)}")
'''
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/_fix_pts.py", "w") as f:
        f.write(test)
    sftp.close()
    
    # Run as www-data to simulate uwsgi
    stdin, stdout, stderr = ssh.exec_command(
        "sudo -u www-data /var/www/html/vidgenerator/.venv/bin/python3 /tmp/_fix_pts.py", timeout=30
    )
    print(">>> Running as www-data:")
    print(stdout.read().decode())
    err = stderr.read().decode().strip()
    if err:
        print(f"STDERR: {err[:500]}")
    
    ssh.close()

if __name__ == "__main__":
    main()

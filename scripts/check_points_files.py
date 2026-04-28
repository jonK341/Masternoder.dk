"""Check points files on production server."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
    
    cmds = [
        "ls -la /var/www/html/logs/unified_points/ 2>&1 | head -20",
        "cat /var/www/html/logs/unified_points/default_user.json 2>&1",
        "cat /var/www/html/logs/unified_points/test_user.json 2>&1",
        "ls -la /var/www/html/logs/ 2>&1 | head -20",
    ]
    for cmd in cmds:
        print(f">>> {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode().strip())
        print()
    
    ssh.close()

if __name__ == "__main__":
    main()

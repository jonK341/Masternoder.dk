"""Check communication psychology points storage."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
    
    cmds = [
        "cat /var/www/html/logs/unified_points/default_user.json 2>&1",
        "cat /var/www/html/logs/unified_points/check_user.json 2>&1",
        "ls -la /var/www/html/logs/unified_points/ 2>&1",
        "find /var/www/html/logs/ -name '*.json' -newer /var/www/html/logs/unified_points/default_user.json -mmin -30 2>/dev/null | head -20",
    ]
    for cmd in cmds:
        print(f">>> {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode().strip())
        print()
    
    ssh.close()

if __name__ == "__main__":
    main()

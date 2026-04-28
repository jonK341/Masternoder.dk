"""Download missing_endpoints_routes.py from server."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_REMOTE = "/var/www/html/vidgenerator"
BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()
    sftp.get(
        f'{BASE_REMOTE}/backend/routes/missing_endpoints_routes.py',
        os.path.join(BASE_LOCAL, 'backend', 'routes', 'missing_endpoints_routes.py')
    )
    sftp.close()
    ssh.close()
    print('Downloaded missing_endpoints_routes.py')

if __name__ == '__main__':
    main()

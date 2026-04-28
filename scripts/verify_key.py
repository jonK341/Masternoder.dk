"""Verify ModelsLab key on server."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)

stdin, stdout, stderr = ssh.exec_command("grep MODELSLAB /var/www/html/.env /var/www/html/vidgenerator/.env 2>&1")
print(stdout.read().decode().strip())

stdin, stdout, stderr = ssh.exec_command("sudo -u www-data cat /var/www/html/.env | grep MODELSLAB 2>&1")
print("www-data read:", stdout.read().decode().strip())

ssh.close()

"""Fix the ModelsLab key line in production .env files."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
KEY = "8t2m1OhTebvkMGVlTseqqBgtGxlr4eWHzJIpzxrQvckG1yBq1jiMXvR2gK6B"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)

for ef in ["/var/www/html/.env", "/var/www/html/vidgenerator/.env"]:
    # Remove the broken concatenated line, then add properly
    cmds = [
        f"sed -i '/MODELSLAB_API_KEY/d' {ef}",
        f"echo '' >> {ef}",
        f"echo 'MODELSLAB_API_KEY={KEY}' >> {ef}",
    ]
    for cmd in cmds:
        ssh.exec_command(cmd)
    
    # Verify
    stdin, stdout, stderr = ssh.exec_command(f"grep -n MODELSLAB {ef}")
    print(f"{ef}: {stdout.read().decode().strip()}")

ssh.close()
print("Fixed.")

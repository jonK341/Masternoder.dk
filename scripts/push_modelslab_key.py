"""Push MODELSLAB_API_KEY to production .env."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
KEY = "8t2m1OhTebvkMGVlTseqqBgtGxlr4eWHzJIpzxrQvckG1yBq1jiMXvR2gK6B"

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)

    env_files = [
        "/var/www/html/.env",
        "/var/www/html/vidgenerator/.env",
    ]
    for ef in env_files:
        stdin, stdout, stderr = ssh.exec_command(f"grep -c MODELSLAB_API_KEY {ef} 2>/dev/null")
        count = stdout.read().decode().strip()
        if count and int(count) > 0:
            ssh.exec_command(f"sed -i 's/^MODELSLAB_API_KEY=.*/MODELSLAB_API_KEY={KEY}/' {ef}")
            print(f"  Updated key in {ef}")
        else:
            ssh.exec_command(f"echo 'MODELSLAB_API_KEY={KEY}' >> {ef}")
            print(f"  Appended key to {ef}")

    # Verify
    for ef in env_files:
        stdin, stdout, stderr = ssh.exec_command(f"grep MODELSLAB {ef} 2>/dev/null")
        line = stdout.read().decode().strip()
        if KEY[:10] in line:
            print(f"  [OK] {ef} verified")
        else:
            print(f"  [!!] {ef}: {line}")

    ssh.close()
    print("\nDone. Restart Flask to activate.")

if __name__ == "__main__":
    main()

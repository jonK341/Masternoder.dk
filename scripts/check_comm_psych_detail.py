"""Check communication psychology detail + AI intelligence log."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
    
    cmds = [
        "cat /var/www/html/logs/communication_psychology/default_user.json 2>&1",
        "python3 -c \"import json; d=json.load(open('/var/www/html/logs/agent_ai_intelligence/intelligence.json')); agents=d.get('agents',{}); print('Agents:', list(agents.keys())); [print(f'  {k}: decisions={v.get(\\\"decisions_made\\\",0)}') for k,v in agents.items()]\"",
    ]
    for cmd in cmds:
        print(f">>> {cmd.split('2>&1')[0].strip() if '2>&1' in cmd else cmd[:80]}...")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode().strip()[:1000])
        print()
    
    ssh.close()

if __name__ == "__main__":
    main()

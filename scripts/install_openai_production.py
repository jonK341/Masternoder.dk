"""Install openai package in production venv."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode().strip(), stderr.read().decode().strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
    
    venv = "/var/www/html/vidgenerator/.venv"
    
    print("[1] Installing openai package...")
    out, err = run_cmd(ssh, f"{venv}/bin/pip install openai", timeout=120)
    print(out[-500:] if len(out) > 500 else out)
    if err:
        print("stderr:", err[:300])
    
    print(f"\n[2] Verify installation...")
    out, _ = run_cmd(ssh, f"{venv}/bin/pip list | grep -i openai")
    print(f"  {out}")
    
    print(f"\n[3] Test LLM call...")
    test = r'''
import sys, os
sys.path.insert(0, "/var/www/html")
os.chdir("/var/www/html")
try:
    from dotenv import load_dotenv
    load_dotenv("/var/www/html/.env")
    load_dotenv("/var/www/html/vidgenerator/.env")
except: pass
key = os.environ.get("OPENAI_API_KEY", "")
print(f"Key length: {len(key)}")
if key:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":"Say hello in 3 words"}],
            max_tokens=20,
            timeout=15,
        )
        print(f"LLM OK: {r.choices[0].message.content}")
    except Exception as e:
        print(f"LLM ERROR: {e}")
else:
    print("No API key")
'''
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/_test_openai.py", "w") as f:
        f.write(test)
    sftp.close()
    out, err = run_cmd(ssh, f"{venv}/bin/python3 /tmp/_test_openai.py", timeout=30)
    print(f"  {out}")
    if err:
        print(f"  stderr: {err[:300]}")
    
    ssh.close()

if __name__ == "__main__":
    main()

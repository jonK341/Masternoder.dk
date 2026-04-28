"""Check if AI/LLM is available on production."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode().strip(), stderr.read().decode().strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
    
    venv = "/var/www/html/vidgenerator/.venv"
    
    print("[1] Check OPENAI_API_KEY in .env...")
    out, _ = run_cmd(ssh, "grep -i OPENAI /var/www/html/.env 2>/dev/null /var/www/html/vidgenerator/.env 2>/dev/null | head -5")
    if out:
        for line in out.split('\n'):
            if 'KEY' in line.upper():
                parts = line.split('=', 1)
                if len(parts) > 1:
                    val = parts[1].strip().strip("'\"")
                    masked = val[:8] + "..." + val[-4:] if len(val) > 12 else "(short/empty)"
                    print(f"  {parts[0].strip()} = {masked}")
                else:
                    print(f"  {line}")
            else:
                print(f"  {line}")
    else:
        print("  NOT FOUND - no OPENAI_API_KEY in .env")
    
    print(f"\n[2] Check openai package in venv...")
    out, _ = run_cmd(ssh, f"{venv}/bin/pip list 2>/dev/null | grep -i openai")
    print(f"  {out or 'NOT INSTALLED'}")
    
    print(f"\n[3] Quick LLM availability test...")
    test = r'''
import sys, os
sys.path.insert(0, "/var/www/html")
os.chdir("/var/www/html")
try:
    from dotenv import load_dotenv
    load_dotenv("/var/www/html/.env")
    load_dotenv("/var/www/html/vidgenerator/.env")
except: pass
from backend.services.llm_service import llm_service
print(f"LLM available: {llm_service.is_available()}")
if llm_service.is_available():
    r = llm_service.complete("Say hello in 3 words", system_prompt="Be brief", max_tokens=20)
    print(f"Test call: success={r.success}, content={r.content}")
else:
    key = os.environ.get("OPENAI_API_KEY", "")
    print(f"Key present: {bool(key)} (len={len(key)})")
'''
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/_check_llm.py", "w") as f:
        f.write(test)
    sftp.close()
    out, err = run_cmd(ssh, f"{venv}/bin/python3 /tmp/_check_llm.py", timeout=30)
    print(f"  {out}")
    if err:
        print(f"  stderr: {err[:300]}")
    
    ssh.close()

if __name__ == "__main__":
    main()

import paramiko

HOST, USER, PASS = "masternoder.dk", "root", "eD)2[K+[S#m_#$3!"
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=20)

def run(cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode('utf-8', errors='replace').strip()

# Try different URL patterns
tests = [
    "http://localhost:5000/api/agent/automation/ai-diagnose",
    "http://localhost:5000/vidgenerator/api/agent/automation/ai-diagnose",
    "https://masternoder.dk/vidgenerator/api/agent/automation/ai-diagnose",
    "http://localhost:5000/api/agent/automation/ai-strategy",
]
for url in tests:
    code = run(f"curl -s -o /dev/null -w '%{{http_code}}' '{url}' --max-time 10", t=15)
    print(f"  {code}  {url}")

print()
# Check what the actual response body is
o = run("curl -s 'http://localhost:5000/api/agent/automation/ai-diagnose' --max-time 10", t=15)
print("Body:", o[:200])
print()
# Also try HEAD and POST
for m in ["HEAD", "POST"]:
    code = run(f"curl -s -o /dev/null -w '%{{http_code}}' -X {m} 'http://localhost:5000/api/agent/automation/ai-diagnose' --max-time 10", t=15)
    print(f"  {m}: {code}")

ssh.close()

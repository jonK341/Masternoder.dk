import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password='eD)2[K+[S#m_#$3!', timeout=20)

def run(cmd, t=15):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode().strip(), err.read().decode().strip()

# Show the context around the system_overview function on server
o, _ = run("sed -n '3765,3790p' /var/www/html/vidgenerator/backend/routes/missing_endpoints_routes.py")
print("Context around system_overview on server:")
print(o)
print()

# Check what routes ARE registered on the running app
o, _ = run("curl -s 'http://localhost:5000/api/system/overview?compact=1' --max-time 5 -w ' STATUS:%{http_code}'")
print("localhost:5000 test:", o)

# Check if uwsgi is running on port 5000
o, _ = run("ss -tlnp | grep 5000")
print("Port 5000:", o)

ssh.close()

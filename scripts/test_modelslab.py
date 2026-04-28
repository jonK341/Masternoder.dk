"""Test ModelsLab availability on production, then generate a clip."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)

    test = r'''
import sys, os
sys.path.insert(0, "/var/www/html")
os.chdir("/var/www/html")

# Load env
try:
    from dotenv import load_dotenv
    for ef in ["/var/www/html/.env", "/var/www/html/vidgenerator/.env"]:
        if os.path.exists(ef):
            load_dotenv(ef, override=True)
except:
    pass

print(f"MODELSLAB_API_KEY set: {bool(os.environ.get('MODELSLAB_API_KEY',''))}")
print(f"Key prefix: {os.environ.get('MODELSLAB_API_KEY','')[:12]}...")

from backend.services.modelslab_video_service import is_available, generate_clip
print(f"is_available(): {is_available()}")

if is_available():
    print("\nGenerating test clip...")
    result = generate_clip(
        prompt="A futuristic city with neon lights and flying cars at night, cinematic",
        negative_prompt="low quality, blurry, watermark",
        width=512,
        height=512,
        num_frames=16,
        fps=15,
        output_type="mp4",
        timeout=120,
    )
    print(f"Result: success={result.get('success')}")
    if result.get('success'):
        print(f"  video_url: {result.get('video_url','')[:100]}")
        print(f"  local_path: {result.get('local_path')}")
    else:
        print(f"  error: {result.get('error')}")
        if result.get('raw'):
            import json
            print(f"  raw: {json.dumps(result['raw'], indent=2)[:500]}")
'''
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/_test_modelslab.py", "w") as f:
        f.write(test)
    sftp.close()

    venv = "/var/www/html/vidgenerator/.venv"
    stdin, stdout, stderr = ssh.exec_command(
        f"sudo -u www-data {venv}/bin/python3 /tmp/_test_modelslab.py",
        timeout=180,
    )
    print(stdout.read().decode())
    err = stderr.read().decode().strip()
    if err:
        print(f"STDERR: {err[:500]}")

    ssh.close()

if __name__ == "__main__":
    main()

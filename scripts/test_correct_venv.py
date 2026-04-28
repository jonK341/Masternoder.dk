"""Test with the correct uwsgi venv: /var/www/html/vidgenerator/.venv"""
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
    
    # Check what python is in the uwsgi venv
    venv = "/var/www/html/vidgenerator/.venv"
    print(f"[1] Check venv python binary...")
    out, _ = run_cmd(ssh, f"ls -la {venv}/bin/python*")
    print(out)
    
    print(f"\n[2] Check moviepy in venv...")
    out, _ = run_cmd(ssh, f"{venv}/bin/python3 -c 'import moviepy; print(moviepy.__version__)' 2>&1")
    print(out)
    
    print(f"\n[3] Check Pillow in venv...")
    out, _ = run_cmd(ssh, f"{venv}/bin/python3 -c 'from PIL import Image; print(\"Pillow OK\")' 2>&1")
    print(out)
    
    print(f"\n[4] Check numpy in venv...")
    out, _ = run_cmd(ssh, f"{venv}/bin/python3 -c 'import numpy; print(numpy.__version__)' 2>&1")
    print(out)
    
    # Write test script and run
    test_script = r'''import sys, os
sys.path.insert(0, "/var/www/html")
os.chdir("/var/www/html")
os.environ["FLASK_ENV"] = "production"
os.environ["VIDEOS_DIR"] = "/var/www/html/vidgenerator/videos"
print("Python:", sys.executable, sys.version)

from backend.services.video_generator_service import (
    _apply_text_overlay, _build_content_fallback_segments, generate_rich_video_sync
)
import numpy as np
from PIL import Image
from moviepy import ImageClip, ColorClip

# Test fallback segments
segs = _build_content_fallback_segments(
    "Machine Learning Basics",
    "This video covers the fundamentals of machine learning including supervised learning, neural networks, and deep learning applications",
    60, True
)
print(f"\nSegments ({len(segs)}):")
for s in segs:
    print(f"  [{s['duration']}s] {s['title']}: {s['description'][:80]}")

# Test overlay returns RGB
w, h = 854, 480
base = ColorClip(size=(w, h), color=(15, 25, 45), duration=3)
clip, used = _apply_text_overlay(base, "Test Title", "Test body text about AI", w, h, 3)
frame = clip.get_frame(0)
print(f"\nFrame shape: {frame.shape} (want 3 channels = RGB)")
clip.close()
base.close()

# Full encode test
print("\nEncoding video with content segments...")
path, err = generate_rich_video_sync("_verify_content_test", segs, width=854, height=480, add_audio=False)
if path and os.path.isfile(path):
    sz = os.path.getsize(path)
    print(f"SUCCESS: {sz} bytes at {path}")
    os.remove(path)
else:
    print(f"FAIL: {err}")
'''
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/_test_encode.py", "w") as f:
        f.write(test_script)
    sftp.close()
    
    print(f"\n[5] Run full encode test with uwsgi venv...")
    out, err = run_cmd(ssh, f"{venv}/bin/python3 /tmp/_test_encode.py", timeout=90)
    print("stdout:", out)
    if err:
        print("stderr:", err[:500])
    
    ssh.close()

if __name__ == "__main__":
    main()

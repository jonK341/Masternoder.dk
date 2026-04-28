"""Verify deployed code on server and test encoding in uwsgi's Python."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
    
    print("=" * 70)
    print("VERIFY DEPLOY AND TEST")
    print("=" * 70)
    
    print("\n[1] Check uwsgi.ini for virtualenv path...")
    out, _ = run_cmd(ssh, "cat /var/www/html/vidgenerator/uwsgi.ini")
    print(out[:1000])
    
    print("\n[2] Check _apply_text_overlay in deployed code (should show RGB, no CompositeVideoClip)...")
    out, _ = run_cmd(ssh, "grep -n 'def _apply_text_overlay\\|CompositeVideoClip\\|Image.new.*RGB\\|method.*chain' /var/www/html/backend/services/video_generator_service.py | head -10")
    print(out)
    
    print("\n[3] Check _build_content_fallback_segments exists...")
    out, _ = run_cmd(ssh, "grep -n 'def _build_content_fallback_segments' /var/www/html/backend/services/video_generator_service.py")
    print(out or "(NOT FOUND - FIX NOT DEPLOYED)")
    
    print("\n[4] Check fast_ai_profile / is_prod in deployed code...")
    out, _ = run_cmd(ssh, "grep -n 'is_prod\\|fast_ai_profile' /var/www/html/backend/services/video_generator_service.py | head -5")
    print(out)
    
    print("\n[5] Check FLASK_ENV in uwsgi env...")
    out, _ = run_cmd(ssh, "grep -i 'FLASK_ENV\\|env\\|virtualenv\\|venv\\|home' /var/www/html/vidgenerator/uwsgi.ini")
    print(out)
    
    print("\n[6] Check the actual python used by uwsgi...")
    out, _ = run_cmd(ssh, "grep -i 'home\\|virtualenv\\|venv\\|pythonpath' /var/www/html/vidgenerator/uwsgi.ini")
    print(out)

    print("\n[7] Run encode test with uwsgi's venv python...")
    test_script = r'''import sys, os
sys.path.insert(0, "/var/www/html")
os.chdir("/var/www/html")
os.environ["FLASK_ENV"] = "production"
os.environ["VIDEOS_DIR"] = "/var/www/html/vidgenerator/videos"
print("Python:", sys.executable)

# Test using our actual code
from backend.services.video_generator_service import _apply_text_overlay, _build_content_fallback_segments, generate_rich_video_sync
import numpy as np
from PIL import Image
from moviepy import ImageClip

# Test _build_content_fallback_segments
segs = _build_content_fallback_segments("My AI Test Title", "This is a detailed description about machine learning and AI content generation", 60, True)
print(f"Segments: {len(segs)}")
for s in segs:
    print(f"  - {s['title']}: {s['description'][:60]}... ({s['duration']}s)")

# Test _apply_text_overlay returns RGB
w, h = 854, 480
from moviepy import ColorClip
base = ColorClip(size=(w, h), color=(15, 25, 45), duration=3)
clip, used = _apply_text_overlay(base, "Test Title", "Test body text", w, h, 3)
frame = clip.get_frame(0)
print(f"Frame shape: {frame.shape} (should be (480, 854, 3) for RGB)")
clip.close()
base.close()

# Test full encode
print("Testing generate_rich_video_sync...")
doc_id = "_verify_test"
path, err = generate_rich_video_sync(doc_id, segs, width=854, height=480, add_audio=False)
if path and os.path.isfile(path):
    sz = os.path.getsize(path)
    print(f"SUCCESS: {path} = {sz} bytes")
    os.remove(path)
else:
    print(f"FAIL: {err}")
'''
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/_verify_test.py", "w") as f:
        f.write(test_script)
    sftp.close()
    
    # Find the venv python used by uwsgi
    out_ini, _ = run_cmd(ssh, "grep -i 'home\\|virtualenv' /var/www/html/vidgenerator/uwsgi.ini | head -1")
    venv_path = ""
    if "=" in out_ini:
        venv_path = out_ini.split("=", 1)[1].strip()
    
    if venv_path:
        python_cmd = os.path.join(venv_path, "bin", "python3")
    else:
        python_cmd = "/var/www/html/vidgenerator/.venv/bin/python3"
    
    # Also try vidgenerator/vidgenerator/.venv
    out_check, _ = run_cmd(ssh, f"test -f {python_cmd} && echo EXISTS || echo MISSING")
    if "MISSING" in out_check:
        python_cmd = "/var/www/html/vidgenerator/vidgenerator/.venv/bin/python3"
        out_check, _ = run_cmd(ssh, f"test -f {python_cmd} && echo EXISTS || echo MISSING")
        if "MISSING" in out_check:
            python_cmd = "/var/www/html/vidgenerator.backup.20251129_002110/.venv/bin/python3"
    
    print(f"\n  Using python: {python_cmd}")
    out, err = run_cmd(ssh, f"{python_cmd} /tmp/_verify_test.py", timeout=90)
    print("  stdout:", out)
    if err:
        print("  stderr:", err[:800])
    
    ssh.close()

if __name__ == "__main__":
    main()

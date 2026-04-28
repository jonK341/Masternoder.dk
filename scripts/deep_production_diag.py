"""Deep production diagnostics: check virtualenv, moviepy, and test encoding."""
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
    print("DEEP PRODUCTION DIAGNOSTICS")
    print("=" * 70)
    
    print("\n[1] Find Python/virtualenv used by uwsgi...")
    out, err = run_cmd(ssh, "cat /etc/uwsgi/apps-enabled/*.ini 2>/dev/null || cat /etc/uwsgi.ini 2>/dev/null || find /etc -name 'uwsgi*' -type f 2>/dev/null | head -5")
    print(out[:1000])
    
    print("\n[2] Check uwsgi process for virtualenv path...")
    out, err = run_cmd(ssh, "ps aux | grep uwsgi | head -5")
    print(out[:800])
    
    print("\n[3] Find where moviepy lives...")
    out, err = run_cmd(ssh, "find / -name 'moviepy' -type d 2>/dev/null | head -5")
    print(out or "(not found)")
    
    print("\n[4] Check pip list for moviepy...")
    out, err = run_cmd(ssh, "pip3 list 2>/dev/null | grep -i movie || pip list 2>/dev/null | grep -i movie")
    print(out or "(not in system pip)")
    
    print("\n[5] Check venv pip...")
    out, err = run_cmd(ssh, "find /var/www -name 'pip' -path '*/bin/pip' 2>/dev/null | head -3")
    if out:
        for pip_path in out.strip().split('\n'):
            o2, _ = run_cmd(ssh, f"{pip_path} list 2>/dev/null | grep -i movie")
            print(f"  {pip_path}: {o2 or '(not found)'}")
    else:
        print("  (no venvs found)")
    
    print("\n[6] Check video files with sizes...")
    out, err = run_cmd(ssh, "ls -la /var/www/html/vidgenerator/videos/*.mp4 2>/dev/null | awk '{print $5, $9}' | sort -n | tail -20")
    print(out)
    
    print("\n[7] Check status sidecars for recent videos...")
    out, err = run_cmd(ssh, "ls -t /var/www/html/vidgenerator/videos/*.status.json 2>/dev/null | head -5")
    if out:
        for f in out.strip().split('\n')[:3]:
            o2, _ = run_cmd(ssh, f"cat {f}")
            print(f"\n  {f}:")
            print(f"  {o2[:300]}")
    else:
        print("  (no status files)")
    
    print("\n[8] Check pipeline files...")
    out, err = run_cmd(ssh, "ls -t /var/www/html/vidgenerator/videos/*.pipeline.json 2>/dev/null | head -3")
    if out:
        for f in out.strip().split('\n')[:2]:
            o2, _ = run_cmd(ssh, f"cat {f}")
            print(f"\n  {f}:")
            print(f"  {o2[:500]}")
    
    print("\n[9] Check uwsgi log for recent errors...")
    out, err = run_cmd(ssh, "journalctl -u uwsgi --no-pager -n 30 2>/dev/null | grep -i -E 'error|traceback|exception|moviepy|ffmpeg|write_videofile' | tail -15")
    print(out[:1000] or "(no errors found)")
    
    print("\n[10] Check uwsgi log for MoviePy import...")
    out, err = run_cmd(ssh, "journalctl -u uwsgi --no-pager -n 100 2>/dev/null | grep -i 'moviepy\\|import.*error\\|ModuleNotFound' | tail -10")
    print(out[:800] or "(nothing)")

    print("\n[11] Write test script to server and run inside uwsgi's python...")
    test_script = r"""
import sys, os
sys.path.insert(0, "/var/www/html")
os.chdir("/var/www/html")
os.environ["FLASK_ENV"] = "production"
os.environ["VIDEOS_DIR"] = "/var/www/html/vidgenerator/videos"
print("Python:", sys.executable, sys.version)
try:
    import moviepy
    print("MoviePy version:", moviepy.__version__)
except ImportError as e:
    print("MoviePy MISSING:", e)
    sys.exit(1)
try:
    from moviepy import ColorClip, ImageClip, concatenate_videoclips
    import numpy as np
    from PIL import Image, ImageDraw
    w, h = 854, 480
    img = Image.new("RGB", (w, h), (15, 25, 45))
    draw = ImageDraw.Draw(img)
    draw.text((60, 70), "Test Title", fill=(0, 255, 136))
    draw.text((60, 120), "Test content from AI generation", fill=(225, 240, 255))
    clip = ImageClip(np.array(img)).with_duration(3)
    out = "/var/www/html/vidgenerator/videos/_diag_test.mp4"
    clip.write_videofile(out, fps=24, codec="libx264", audio=False, logger=None, preset="ultrafast", ffmpeg_params=["-pix_fmt","yuv420p","-movflags","+faststart"])
    sz = os.path.getsize(out)
    clip.close()
    os.remove(out)
    print(f"ENCODE OK: {sz} bytes")
except Exception as e:
    print(f"ENCODE FAIL: {e}")
    import traceback
    traceback.print_exc()
"""
    # Write to a temp file on the server
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/_diag_encode_test.py", "w") as f:
        f.write(test_script)
    sftp.close()
    
    # Find the right python
    out_py, _ = run_cmd(ssh, "find /var/www -name 'python3' -path '*/bin/python3' 2>/dev/null | head -1")
    python_cmd = out_py.strip() if out_py.strip() else "python3"
    print(f"  Using python: {python_cmd}")
    out, err = run_cmd(ssh, f"{python_cmd} /tmp/_diag_encode_test.py", timeout=60)
    print("  stdout:", out)
    if err:
        print("  stderr:", err[:500])
    
    ssh.close()

if __name__ == "__main__":
    main()

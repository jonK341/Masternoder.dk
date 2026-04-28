"""Kill lingering ffmpeg on production and run test."""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
    
    print("[1] Killing lingering ffmpeg processes...")
    stdin, stdout, stderr = ssh.exec_command('pkill -9 -f ffmpeg 2>/dev/null; echo DONE')
    print("  ", stdout.read().decode().strip())
    
    print("[2] Checking video dir...")
    stdin, stdout, stderr = ssh.exec_command('ls -la /var/www/html/vidgenerator/videos/ | tail -10')
    print("  ", stdout.read().decode().strip())
    
    print("[3] Checking ffmpeg version...")
    stdin, stdout, stderr = ssh.exec_command('ffmpeg -version | head -1')
    print("  ", stdout.read().decode().strip())
    
    print("[4] Checking moviepy version...")
    stdin, stdout, stderr = ssh.exec_command('python3 -c "import moviepy; print(moviepy.__version__)"')
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    print("  ", out or err)
    
    print("[5] Quick local encode test on server...")
    test_script = '''
import sys, os
sys.path.insert(0, "/var/www/html")
os.chdir("/var/www/html")
os.environ.setdefault("FLASK_ENV", "production")
os.environ.setdefault("VIDEOS_DIR", "/var/www/html/vidgenerator/videos")

try:
    from moviepy import ColorClip, ImageClip, concatenate_videoclips
    import numpy as np
    from PIL import Image, ImageDraw
    
    w, h = 854, 480
    segments = [
        ("Intro: AI Content Test", "This video tests AI content generation with real text overlays"),
        ("Chapter 1", "Background information about the topic including detailed description"),
        ("Summary", "Final conclusions and wrap-up of the content presented"),
    ]
    clips = []
    colors = [(15,25,45),(25,45,85),(45,65,105)]
    for i, (title, body) in enumerate(segments):
        img = Image.new("RGB", (w, h), colors[i % len(colors)])
        draw = ImageDraw.Draw(img)
        font = ImageDraw.ImageDraw.font  # default
        draw.text((60, 70), title, fill=(0,255,136))
        y = 120
        for word_chunk in [body[j:j+60] for j in range(0, len(body), 60)]:
            draw.text((60, y), word_chunk, fill=(225,240,255))
            y += 20
        clip = ImageClip(np.array(img)).with_duration(4)
        clips.append(clip)
    
    final = concatenate_videoclips(clips, method="chain")
    out = "/var/www/html/vidgenerator/videos/test_encode_check.mp4"
    final.write_videofile(out, fps=24, codec="libx264", audio=False, logger=None, preset="ultrafast", ffmpeg_params=["-pix_fmt","yuv420p","-movflags","+faststart"])
    sz = os.path.getsize(out)
    print(f"SUCCESS: {out} = {sz} bytes")
    for c in clips:
        c.close()
    final.close()
    os.remove(out)
except Exception as e:
    print(f"FAIL: {e}")
'''
    stdin, stdout, stderr = ssh.exec_command(f'python3 -c {repr(test_script)}', timeout=60)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    print("  stdout:", out)
    if err:
        print("  stderr:", err[:500])
    
    ssh.close()

if __name__ == "__main__":
    main()

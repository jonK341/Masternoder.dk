"""Test audio generation components on the server."""
import paramiko
import time
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

test_script = r"""
import sys, os
sys.path.insert(0, '/var/www/html')
os.environ['VIDEOS_DIR'] = '/var/www/html/vidgenerator/videos'

print("=== Test 1: Dynamic Audio ===")
try:
    from backend.services.video_generator_service import _build_dynamic_audio_clip
    segments = [{"title": "Test", "description": "Hello world", "duration": 5}]
    audio = _build_dynamic_audio_clip(10.0, segments, {"style": "cinematic", "intensity": "high", "transitions": True, "fades": True})
    if audio is not None:
        print(f"  Audio clip: duration={audio.duration}, fps={audio.fps}")
    else:
        print("  Audio returned None")
except Exception as e:
    print(f"  Error: {e}")
    import traceback; traceback.print_exc()

print("\n=== Test 2: TTS ===")
try:
    from backend.services.tts_service import is_available, generate_speech
    print(f"  TTS available: {is_available()}")
    if is_available():
        path = generate_speech("This is a test of text to speech narration.", dest_path="/tmp/tts_test.mp3")
        if path:
            size = os.path.getsize(path)
            print(f"  TTS file: {path}, size: {size} bytes")
        else:
            print("  TTS returned None")
except Exception as e:
    print(f"  Error: {e}")
    import traceback; traceback.print_exc()

print("\n=== Test 3: MoviePy Audio Write ===")
try:
    from moviepy import ColorClip, AudioClip
    import numpy as np
    def make_frame(t):
        arr = np.atleast_1d(np.array(t, dtype=np.float64))
        signal = 0.3 * np.sin(2 * 3.14159 * 440 * arr)
        return np.column_stack([signal, signal]).astype(np.float32)
    audio = AudioClip(make_frame, duration=5.0, fps=44100)
    clip = ColorClip((320, 240), (50, 50, 50), duration=5.0).with_audio(audio)
    test_path = "/tmp/test_audio_video.mp4"
    clip.write_videofile(test_path, fps=24, codec="libx264", audio=True, audio_codec="aac", logger=None, preset="ultrafast", ffmpeg_params=["-pix_fmt", "yuv420p"])
    size = os.path.getsize(test_path) if os.path.isfile(test_path) else 0
    print(f"  Written: {test_path}, size: {size} bytes")
    import subprocess
    result = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", test_path], capture_output=True, text=True)
    for line in result.stdout.split("\n"):
        if "nb_streams" in line or "duration" in line:
            print(f"  {line.strip()}")
except Exception as e:
    print(f"  Error: {e}")
    import traceback; traceback.print_exc()
"""

sftp = ssh.open_sftp()
with sftp.open("/tmp/test_audio.py", "w") as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command(
    "/var/www/html/vidgenerator/.venv/bin/python3 /tmp/test_audio.py 2>&1"
)
time.sleep(15)
out = stdout.read().decode(errors='replace')
print(out[:4000])

import os
ssh.close()

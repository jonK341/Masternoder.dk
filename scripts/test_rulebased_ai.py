"""Test rule-based AI on production server."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
    
    test = r'''
import sys, os, json, traceback
sys.path.insert(0, "/var/www/html")
os.chdir("/var/www/html")
os.environ["FLASK_ENV"] = "production"
os.environ["VIDEOS_DIR"] = "/var/www/html/vidgenerator/videos"

# Test 1: Can we import agent_ai_intelligence?
print("=== Test 1: Import agent_ai_intelligence ===")
try:
    from backend.services.agent_ai_intelligence import agent_ai_intelligence
    print(f"OK: type={type(agent_ai_intelligence)}")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()

# Test 2: Can we call develop_strategy?
print("\n=== Test 2: develop_strategy ===")
try:
    strat = agent_ai_intelligence.develop_strategy(
        "test_agent", goal="create_video:TestTitle",
        constraints={"topic": "machine learning", "segments": 3}
    )
    print(f"OK: phases={len(strat.get('phases', []))}")
    for p in strat.get("phases", []):
        print(f"  Phase {p.get('phase')}: {p.get('action')}")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()

# Test 3: Can we call predict_outcome?
print("\n=== Test 3: predict_outcome ===")
try:
    pred = agent_ai_intelligence.predict_outcome(
        "test_agent",
        action={"type": "encode_video", "segments": 3},
        context={"prompt_length": 100, "segment_count": 3}
    )
    print(f"OK: confidence={pred.get('confidence')}")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()

# Test 4: Can we import _rulebased_ai_enrich?
print("\n=== Test 4: Import _rulebased_ai_enrich ===")
try:
    from backend.services.video_generator_service import _rulebased_ai_enrich
    print("OK: function imported")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()

# Test 5: Run _rulebased_ai_enrich
print("\n=== Test 5: Run _rulebased_ai_enrich ===")
try:
    segments = [
        {"title": "Test Title", "description": "Test description about AI", "duration": 5},
        {"title": "Chapter 1", "description": "More about AI technology", "duration": 6},
        {"title": "Summary", "description": "Conclusion of the video", "duration": 4},
    ]
    result = _rulebased_ai_enrich(segments, "Test Title", "Test prompt about AI", "test_user")
    print(f"OK: {len(result)} segments returned")
    for s in result:
        print(f"  Title: {s.get('title')}")
        print(f"  Tagline: {s.get('tagline', '(none)')}")
        print(f"  Mood: {s.get('mood', '(none)')}")
        print(f"  BG: {s.get('bg_color', '(none)')}")
        print(f"  Desc: {s.get('description', '')[:80]}")
        print()
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()

# Test 6: ai_skill_implementations
print("\n=== Test 6: ai_skill_implementations ===")
try:
    from backend.services.ai_skill_implementations import ai_skills
    opt = ai_skills.content_optimization("Test content about AI", "engagement", "test_agent")
    print(f"OK: {opt}")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()
'''
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/_test_rulebased.py", "w") as f:
        f.write(test)
    sftp.close()
    
    venv = "/var/www/html/vidgenerator/.venv"
    stdin, stdout, stderr = ssh.exec_command(f"{venv}/bin/python3 /tmp/_test_rulebased.py", timeout=30)
    print(stdout.read().decode())
    err = stderr.read().decode().strip()
    if err:
        print("STDERR:", err[:500])
    
    ssh.close()

if __name__ == "__main__":
    main()

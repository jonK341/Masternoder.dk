"""Comprehensive check of ALL points systems on production."""
import paramiko, os, json

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)

    test_script = r'''
import sys, os, json, traceback
sys.path.insert(0, "/var/www/html")
os.chdir("/var/www/html")

results = {}

# ============================================================
# 1. Unified Points DB (primary)
# ============================================================
print("=" * 60)
print("1. UNIFIED POINTS DB")
print("=" * 60)
try:
    from backend.services.unified_points_database import unified_points_db
    if unified_points_db:
        r = unified_points_db.add_points("check_user", "generation_points", 10, source="system_check")
        print(f"  add_points: {r.get('success', False)}")
        pts = unified_points_db.get_all_points("check_user")
        systems = pts.get("points", pts).get("systems", {}) if isinstance(pts, dict) else {}
        print(f"  get_all_points: {len(systems)} types, gen_pts={systems.get('generation_points', 0)}")
        results["unified_points_db"] = "OK"
    else:
        print("  NONE - not initialized")
        results["unified_points_db"] = "NONE"
except Exception as e:
    print(f"  FAIL: {e}")
    results["unified_points_db"] = f"FAIL: {e}"

# ============================================================
# 2. Enhanced Unified Points DB
# ============================================================
print("\n" + "=" * 60)
print("2. ENHANCED UNIFIED POINTS DB")
print("=" * 60)
try:
    from backend.services.unified_points_database_enhanced import unified_points_db_enhanced
    if unified_points_db_enhanced:
        r = unified_points_db_enhanced.add_points("check_user", "generation_points", 5, source="system_check")
        print(f"  add_points: {r.get('success', False)}")
        results["unified_points_db_enhanced"] = "OK"
    else:
        print("  NONE")
        results["unified_points_db_enhanced"] = "NONE"
except Exception as e:
    print(f"  FAIL: {e}")
    results["unified_points_db_enhanced"] = f"FAIL: {e}"

# ============================================================
# 3. Trigger Integration
# ============================================================
print("\n" + "=" * 60)
print("3. UNIFIED POINTS TRIGGER INTEGRATION")
print("=" * 60)
try:
    from backend.services.unified_points_trigger_integration import unified_points_trigger_integration
    if unified_points_trigger_integration:
        r = unified_points_trigger_integration.award_points_with_trigger(
            "video_generation", user_id="check_user", amount=5, metadata={"test": True}
        )
        print(f"  award_points_with_trigger: {r}")
        results["trigger_integration"] = "OK"
    else:
        print("  NONE")
        results["trigger_integration"] = "NONE"
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    results["trigger_integration"] = f"FAIL: {e}"

# ============================================================
# 4. Communication Psychology
# ============================================================
print("\n" + "=" * 60)
print("4. COMMUNICATION PSYCHOLOGY")
print("=" * 60)
try:
    from backend.services.communication_psychology_service import award_points_for_activity
    r = award_points_for_activity(
        "check_user", amount=15, source_activity="system_check",
        metadata={"test": True}
    )
    print(f"  award_points_for_activity: {r}")
    results["communication_psychology"] = "OK"
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    results["communication_psychology"] = f"FAIL: {e}"

# ============================================================
# 5. Trophies
# ============================================================
print("\n" + "=" * 60)
print("5. TROPHIES")
print("=" * 60)
try:
    from backend.services.trophies_db_service import award_trophy, get_user_trophies
    r = award_trophy("check_user", "first_video")
    print(f"  award_trophy: {r}")
    trophies = get_user_trophies("check_user")
    print(f"  get_user_trophies: {len(trophies) if isinstance(trophies, list) else trophies}")
    results["trophies"] = "OK"
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    results["trophies"] = f"FAIL: {e}"

# ============================================================
# 6. User Onboarding / Profile
# ============================================================
print("\n" + "=" * 60)
print("6. USER ONBOARDING / PROFILE")
print("=" * 60)
try:
    from backend.services.user_onboarding import user_onboarding
    if user_onboarding:
        profile = user_onboarding.get_user_profile("check_user")
        print(f"  get_user_profile: {type(profile).__name__}, keys={list((profile or {}).keys())[:8]}")
        results["user_onboarding"] = "OK"
    else:
        print("  NONE")
        results["user_onboarding"] = "NONE"
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    results["user_onboarding"] = f"FAIL: {e}"

# ============================================================
# 7. Agent AI Intelligence (learning)
# ============================================================
print("\n" + "=" * 60)
print("7. AGENT AI INTELLIGENCE")
print("=" * 60)
try:
    from backend.services.agent_ai_intelligence import agent_ai_intelligence as ai_intel
    r = ai_intel.learn_from_experience("check_agent", {"type": "system_check", "result": "ok"})
    print(f"  learn_from_experience: {r.get('success', False) if isinstance(r, dict) else r}")
    intel = ai_intel.get_agent_intelligence("check_agent")
    print(f"  get_agent_intelligence: decisions={intel.get('decisions_made', 0)}")
    results["agent_ai_intelligence"] = "OK"
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    results["agent_ai_intelligence"] = f"FAIL: {e}"

# ============================================================
# 8. Agent Trigger System
# ============================================================
print("\n" + "=" * 60)
print("8. AGENT TRIGGER SYSTEM")
print("=" * 60)
try:
    from backend.services.agent_trigger_system import agent_trigger_system
    r = agent_trigger_system.award_points("video_generation", "check_user", {"amount": 5})
    print(f"  award_points: {r}")
    results["agent_trigger_system"] = "OK"
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    results["agent_trigger_system"] = f"FAIL: {e}"

# ============================================================
# 9. Points Analytics
# ============================================================
print("\n" + "=" * 60)
print("9. POINTS ANALYTICS (points_db_service)")
print("=" * 60)
try:
    from backend.services.points_db_service import points_analytics_tables_exist, point_transactions_exist
    tables = points_analytics_tables_exist()
    txns = point_transactions_exist()
    print(f"  analytics_tables_exist: {tables}")
    print(f"  point_transactions_exist: {txns}")
    results["points_analytics"] = f"tables={tables}, txns={txns}"
except Exception as e:
    print(f"  FAIL: {e}")
    results["points_analytics"] = f"FAIL: {e}"

# ============================================================
# 10. AI Skill Implementations (content optimization)
# ============================================================
print("\n" + "=" * 60)
print("10. AI SKILL IMPLEMENTATIONS")
print("=" * 60)
try:
    from backend.services.ai_skill_implementations import ai_skill_implementations
    r = ai_skill_implementations.content_optimization("test video content", "engagement", "check_agent")
    print(f"  content_optimization: success={r.get('success', False)}")
    results["ai_skill_implementations"] = "OK"
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    results["ai_skill_implementations"] = f"FAIL: {e}"

# ============================================================
# 11. AI Content Generator
# ============================================================
print("\n" + "=" * 60)
print("11. AI CONTENT GENERATOR")
print("=" * 60)
try:
    from backend.services.ai_content_generator import ai_content_generator
    r = ai_content_generator.generate_content("strategy", {"goal": "video_quality"}, agent_class="check_agent")
    print(f"  generate_content(strategy): type={type(r).__name__}, keys={list((r or {}).keys())[:5] if isinstance(r, dict) else 'N/A'}")
    results["ai_content_generator"] = "OK"
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    results["ai_content_generator"] = f"FAIL: {e}"

# ============================================================
# 12. LLM Service (circuit breaker check)
# ============================================================
print("\n" + "=" * 60)
print("12. LLM SERVICE (circuit breaker)")
print("=" * 60)
try:
    from backend.services import llm_service
    print(f"  API key set: {bool(llm_service.OPENAI_API_KEY)}")
    print(f"  Circuit open until: {llm_service._circuit_open_until}")
    avail = llm_service.is_available()
    print(f"  is_available: {avail}")
    results["llm_service"] = f"key={'yes' if llm_service.OPENAI_API_KEY else 'no'}, available={avail}"
except Exception as e:
    print(f"  FAIL: {e}")
    results["llm_service"] = f"FAIL: {e}"

# ============================================================
# FINAL: Read default_user points file
# ============================================================
print("\n" + "=" * 60)
print("CURRENT default_user POINTS")
print("=" * 60)
try:
    path = "/var/www/html/logs/unified_points/default_user.json"
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        print(json.dumps(data, indent=2))
    else:
        print("  File not found")
except Exception as e:
    print(f"  FAIL: {e}")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for name, status in results.items():
    icon = "OK" if "OK" in str(status) or "True" in str(status) else "!!"
    print(f"  [{icon}] {name:40s} {status}")
'''

    sftp = ssh.open_sftp()
    with sftp.file("/tmp/_check_all_points.py", "w") as f:
        f.write(test_script)
    sftp.close()

    venv = "/var/www/html/vidgenerator/.venv"
    stdin, stdout, stderr = ssh.exec_command(
        f"sudo -u www-data {venv}/bin/python3 /tmp/_check_all_points.py 2>&1",
        timeout=60,
    )
    output = stdout.read().decode()
    # Filter out blueprint registration noise
    lines = output.split("\n")
    for line in lines:
        if "[OK] Registered" in line or "[WARN] Could not import" in line or "[SUMMARY] Registered" in line:
            continue
        if "Warning: Could not register" in line:
            continue
        print(line)

    ssh.close()

if __name__ == "__main__":
    main()

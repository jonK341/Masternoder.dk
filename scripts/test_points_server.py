"""Test points systems directly on the production server."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
    
    test = r'''
import sys, os, traceback
sys.path.insert(0, "/var/www/html")
os.chdir("/var/www/html")

print("=== Test 1: Import unified_points_db ===")
try:
    from backend.services.unified_points_database import unified_points_db
    print(f"OK: type={type(unified_points_db)}, is_none={unified_points_db is None}")
    if unified_points_db:
        print(f"  has add_points: {hasattr(unified_points_db, 'add_points')}")
        print(f"  has get_all_points: {hasattr(unified_points_db, 'get_all_points')}")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()

print("\n=== Test 2: Add test points ===")
try:
    result = unified_points_db.add_points("test_user", "generation_points", 50, source="test", metadata={"test": True})
    print(f"Result: {result}")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()

print("\n=== Test 3: Read points back ===")
try:
    pts = unified_points_db.get_all_points("test_user")
    print(f"Points: {pts}")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()

print("\n=== Test 4: Check default_user points ===")
try:
    pts = unified_points_db.get_all_points("default_user")
    systems = pts.get("systems", {}) if isinstance(pts, dict) else {}
    non_zero = {k: v for k, v in systems.items() if v}
    print(f"Non-zero systems: {non_zero}")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()

print("\n=== Test 5: Import enhanced DB ===")
try:
    from backend.services.unified_points_database_enhanced import unified_points_db_enhanced
    print(f"OK: type={type(unified_points_db_enhanced)}, is_none={unified_points_db_enhanced is None}")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()

print("\n=== Test 6: Import trigger integration ===")
try:
    from backend.services.unified_points_trigger_integration import unified_points_trigger_integration
    print(f"OK: type={type(unified_points_trigger_integration)}")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()

print("\n=== Test 7: Check DB file / storage ===")
try:
    db_attr = getattr(unified_points_db, 'db_path', None) or getattr(unified_points_db, 'data_file', None)
    print(f"DB path attribute: {db_attr}")
    data_dir = getattr(unified_points_db, 'data_dir', None) or getattr(unified_points_db, 'base_dir', None)
    print(f"Data dir attribute: {data_dir}")
    storage = getattr(unified_points_db, 'storage', None) or getattr(unified_points_db, 'points', None) or getattr(unified_points_db, 'data', None)
    if isinstance(storage, dict):
        print(f"In-memory storage keys: {list(storage.keys())[:10]}")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()
'''
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/_test_points.py", "w") as f:
        f.write(test)
    sftp.close()
    
    venv = "/var/www/html/vidgenerator/.venv"
    stdin, stdout, stderr = ssh.exec_command(f"{venv}/bin/python3 /tmp/_test_points.py", timeout=30)
    print(stdout.read().decode())
    err = stderr.read().decode().strip()
    if err:
        print("STDERR:", err[:800])
    
    ssh.close()

if __name__ == "__main__":
    main()

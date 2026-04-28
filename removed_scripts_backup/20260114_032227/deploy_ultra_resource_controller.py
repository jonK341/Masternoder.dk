"""
Auto Deploy and Restart Services for Ultra Resource Controller
Deploys all new systems and restarts necessary services
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"[ACTION] {description}")
    print(f"{'='*60}")
    print(f"Command: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"[OK] Success")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"[ERROR] Error (code: {result.returncode})")
            if result.stderr:
                print(f"Error output: {result.stderr}")
            if result.stdout:
                print(f"Output: {result.stdout}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] Timeout (30s)")
        return False
    except Exception as e:
        print(f"[EXCEPTION] Exception: {e}")
        return False

def check_service_status(service_name):
    """Check if a service is running"""
    try:
        result = subprocess.run(
            f"sudo systemctl is-active {service_name}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0 and result.stdout.strip() == 'active'
    except Exception as e:
        print(f"Warning: Could not check {service_name}: {e}")
        return False

def deploy():
    """Main deployment function"""
    print("\n" + "="*60)
    print("AUTO DEPLOY: Ultra Resource Controller & All New Systems")
    print("="*60)
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    print(f"\n[INFO] Working directory: {os.getcwd()}")
    
    # Step 1: Clear Python cache
    print("\n" + "="*60)
    print("Step 1: Clearing Python cache")
    print("="*60)
    
    cache_dirs = [
        "__pycache__",
        "backend/__pycache__",
        "backend/services/__pycache__",
        "backend/routes/__pycache__"
    ]
    
    for cache_dir in cache_dirs:
        cache_path = Path(cache_dir)
        if cache_path.exists():
            try:
                import shutil
                shutil.rmtree(cache_path)
                print(f"[OK] Cleared: {cache_dir}")
            except Exception as e:
                print(f"[WARN] Warning: Could not clear {cache_dir}: {e}")
    
    # Step 2: Verify Python files compile
    print("\n" + "="*60)
    print("Step 2: Verifying Python files")
    print("="*60)
    
    files_to_check = [
        "backend/services/ultra_resource_controller.py",
        "backend/routes/ultra_resource_controller_routes.py",
        "backend/services/unified_game_mechanics_constructor.py",
        "backend/services/enhanced_tech_tree_with_quests.py",
        "backend/services/enhanced_skills_system.py",
        "backend/services/unified_point_system_json_storage.py",
        "backend/services/enhanced_user_profile_json.py",
        "backend/services/skill_reward_system.py",
        "backend/services/calendar_planner_system.py",
        "backend/services/groups_system.py",
        "backend/services/cognitive_behavior_scanner.py",
        "backend/services/decision_trees_system.py",
        "backend/services/todos_pause_system.py",
        "backend/routes/unified_game_mechanics_routes.py",
        "backend/routes/enhanced_systems_routes.py",
        "backend/routes/new_systems_routes.py"
    ]
    
    all_valid = True
    for file_path in files_to_check:
        file = Path(file_path)
        if file.exists():
            result = run_command(
                f"python -m py_compile {file_path}",
                f"Checking {file_path}"
            )
            if not result:
                all_valid = False
        else:
            print(f"[WARN] File not found: {file_path}")
    
    if not all_valid:
        print("\n[ERROR] Some files failed compilation. Please fix errors before deploying.")
        return False
    
    # Step 3: Restart uWSGI
    print("\n" + "="*60)
    print("Step 3: Restarting uWSGI")
    print("="*60)
    
    uwsgi_restart = run_command(
        "sudo systemctl restart uwsgi",
        "Restarting uWSGI service"
    )
    
    if uwsgi_restart:
        time.sleep(2)
        if check_service_status("uwsgi"):
            print("[OK] uWSGI is running")
        else:
            print("[WARN] uWSGI status unknown")
    
    # Step 4: Restart Python Proxy
    print("\n" + "="*60)
    print("Step 4: Restarting Python Proxy")
    print("="*60)
    
    proxy_restart = run_command(
        "sudo systemctl restart python-proxy",
        "Restarting python-proxy service"
    )
    
    if proxy_restart:
        time.sleep(2)
        if check_service_status("python-proxy"):
            print("[OK] python-proxy is running")
        else:
            print("[WARN] python-proxy status unknown")
    
    # Step 5: Restart Apache (if needed)
    print("\n" + "="*60)
    print("Step 5: Restarting Apache (optional)")
    print("="*60)
    
    apache_restart = run_command(
        "sudo systemctl restart apache2",
        "Restarting Apache service"
    )
    
    # Step 6: Verify services
    print("\n" + "="*60)
    print("Step 6: Verifying services")
    print("="*60)
    
    services = ["uwsgi", "python-proxy", "apache2"]
    all_running = True
    
    for service in services:
        if check_service_status(service):
            print(f"[OK] {service}: Running")
        else:
            print(f"[WARN] {service}: Status unknown or not running")
            all_running = False
    
    # Step 7: Test endpoints (optional)
    print("\n" + "="*60)
    print("Step 7: Testing endpoints (optional)")
    print("="*60)
    
    test_endpoints = [
        "/vidgenerator/api/ultra-resource/energy?user_id=test",
        "/vidgenerator/api/game-mechanics/subjects?user_id=test",
        "/vidgenerator/api/skill-reward/completions?user_id=test"
    ]
    
    print("Note: Endpoint testing requires server to be fully started.")
    print("Wait a few seconds after restart before testing.")
    
    # Summary
    print("\n" + "="*60)
    print("DEPLOYMENT SUMMARY")
    print("="*60)
    
    print(f"\n[STATUS] Python files: {'Valid' if all_valid else 'Some errors'}")
    print(f"[INFO] Services: Must be restarted manually on server")
    
    if all_valid:
        print("\n[SUCCESS] CODE VALIDATION COMPLETE!")
        print("\n[NEXT STEPS]")
        print("1. Deploy files to server (if not already there)")
        print("2. SSH to server and restart services:")
        print("   ssh root@masternoder.dk")
        print("   sudo systemctl restart uwsgi")
        print("   sudo systemctl restart python-proxy")
        print("3. Wait 5-10 seconds for services to fully start")
        print("4. Test endpoints:")
        print("   - https://masternoder.dk/vidgenerator/api/ultra-resource/energy?user_id=test")
        print("   - https://masternoder.dk/vidgenerator/api/game-mechanics/subjects?user_id=test")
        print("5. Check logs if issues:")
        print("   - sudo tail -f /var/log/uwsgi/app.log")
        print("   - sudo journalctl -u uwsgi -f")
        return True
    else:
        print("\n[ERROR] CODE VALIDATION FAILED")
        print("Please fix errors before deploying.")
        return False

if __name__ == "__main__":
    try:
        success = deploy()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARN] Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Deployment failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


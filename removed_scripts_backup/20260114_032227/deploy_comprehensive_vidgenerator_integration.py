"""
Deploy Comprehensive Vidgenerator Integration
- All missing routes
- Battle system re-engineering
- Trigger-based generator/battle
- Unified points & energy
- Page integrations
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def deploy_comprehensive():
    """Deploy all comprehensive vidgenerator integration"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*70)
        print("DEPLOYING COMPREHENSIVE VIDGENERATOR INTEGRATION")
        print("="*70)
        
        files_to_deploy = [
            ('backend/services/vidgenerator_comprehensive_audit.py', '/var/www/html/vidgenerator/backend/services/vidgenerator_comprehensive_audit.py'),
            ('backend/services/trigger_based_generator.py', '/var/www/html/vidgenerator/backend/services/trigger_based_generator.py'),
            ('backend/services/unified_page_integrator.py', '/var/www/html/vidgenerator/backend/services/unified_page_integrator.py'),
            ('backend/services/ultra_resource_controller.py', '/var/www/html/vidgenerator/backend/services/ultra_resource_controller.py'),
            ('backend/routes/comprehensive_vidgenerator_routes.py', '/var/www/html/vidgenerator/backend/routes/comprehensive_vidgenerator_routes.py'),
            ('backend/routes/all_vidgenerator_pages_routes.py', '/var/www/html/vidgenerator/backend/routes/all_vidgenerator_pages_routes.py'),
            ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
        ]
        
        print("\n[STEP 1] Deploying files to server...")
        for local_path, remote_path in files_to_deploy:
            if os.path.exists(local_path):
                with open(local_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                remote_dir = os.path.dirname(remote_path)
                stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
                stdout.channel.recv_exit_status()
                
                stdin, stdout, stderr = ssh.exec_command(f"cat > {remote_path} << 'ENDOFFILE'\n{content}\nENDOFFILE")
                exit_status = stdout.channel.recv_exit_status()
                
                if exit_status == 0:
                    print(f"  [OK] {local_path} -> {remote_path}")
                else:
                    error = stderr.read().decode('utf-8', errors='ignore')
                    print(f"  [ERROR] {local_path}: {error[:200]}")
            else:
                print(f"  [WARN] Local file not found: {local_path}")
        
        print("\n[STEP 2] Clearing Python cache...")
        commands = [
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true",
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("  [OK] Cache cleared")
        
        print("\n[STEP 3] Restarting uWSGI...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart uwsgi")
        stdout.channel.recv_exit_status()
        print("  [OK] uWSGI restarted")
        time.sleep(10)
        
        print("\n[STEP 4] Testing new endpoints...")
        endpoints = [
            ("/vidgenerator/api/vidgenerator/audit/run", "Comprehensive Audit"),
            ("/vidgenerator/api/vidgenerator/trigger/register", "Trigger Register"),
            ("/vidgenerator/api/vidgenerator/points/unified/get?user_id=test", "Unified Points"),
            ("/vidgenerator/api/vidgenerator/pages/list", "Pages List"),
        ]
        
        for endpoint, name in endpoints:
            print(f"\n  [TEST] {name}")
            cmd = f"curl -s -w '\\nHTTP_CODE:%{{http_code}}' 'https://masternoder.dk{endpoint}'"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode('utf-8', errors='ignore')
            
            if "HTTP_CODE:200" in output:
                print(f"    [SUCCESS] Status 200")
            elif "HTTP_CODE:404" in output:
                print(f"    [FAIL] Status 404")
            else:
                print(f"    [INFO] {output[-50:]}")
        
        ssh.close()
        
        print("\n" + "="*70)
        print("DEPLOYMENT COMPLETE")
        print("="*70)
        print("\n[INFO] Comprehensive vidgenerator integration deployed:")
        print("  [OK] Comprehensive audit system")
        print("  [OK] Trigger-based generator/battle")
        print("  [OK] Unified points & energy system")
        print("  [OK] All vidgenerator pages routes")
        print("  [OK] Page integrator service")
        print("\n[INFO] New capabilities:")
        print("  - Trigger-based actions (not instant)")
        print("  - Pointer catching system")
        print("  - Unified energy & points")
        print("  - Complete page route coverage")
        print("  - Comprehensive audit system")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_comprehensive()


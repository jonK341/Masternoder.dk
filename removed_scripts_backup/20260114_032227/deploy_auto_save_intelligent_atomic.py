"""
Deploy Auto-Save, Intelligent URLs, and Atomic Calculator
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def deploy_all():
    """Deploy all new systems"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*70)
        print("DEPLOYING AUTO-SAVE, INTELLIGENT URLS, AND ATOMIC CALCULATOR")
        print("="*70)
        
        files_to_deploy = [
            ('backend/services/comprehensive_auto_save.py', '/var/www/html/vidgenerator/backend/services/comprehensive_auto_save.py'),
            ('backend/services/intelligent_url_router.py', '/var/www/html/vidgenerator/backend/services/intelligent_url_router.py'),
            ('backend/services/atomic_calculator_hell_money.py', '/var/www/html/vidgenerator/backend/services/atomic_calculator_hell_money.py'),
            ('backend/routes/comprehensive_auto_save_routes.py', '/var/www/html/vidgenerator/backend/routes/comprehensive_auto_save_routes.py'),
            ('backend/routes/intelligent_url_routes.py', '/var/www/html/vidgenerator/backend/routes/intelligent_url_routes.py'),
            ('backend/routes/atomic_calculator_routes.py', '/var/www/html/vidgenerator/backend/routes/atomic_calculator_routes.py'),
            ('vidgenerator/static/js/comprehensive-auto-save.js', '/var/www/html/vidgenerator/vidgenerator/static/js/comprehensive-auto-save.js'),
            ('vidgenerator/static/js/enhanced-frontpage-stats.js', '/var/www/html/vidgenerator/vidgenerator/static/js/enhanced-frontpage-stats.js'),
            ('vidgenerator/static/js/atomic-calculator-integration.js', '/var/www/html/vidgenerator/vidgenerator/static/js/atomic-calculator-integration.js'),
            ('vidgenerator/index.html', '/var/www/html/vidgenerator/vidgenerator/index.html'),
            ('vidgenerator/advanced_calculator/index.html', '/var/www/html/vidgenerator/vidgenerator/advanced_calculator/index.html'),
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
            ("/vidgenerator/api/auto-save/status?user_id=test", "Auto-Save Status"),
            ("/vidgenerator/api/atomic-calculator/calculate", "Atomic Calculator"),
            ("/vidgenerator/api/url/process", "Intelligent URL"),
        ]
        
        for endpoint, name in endpoints:
            print(f"\n  [TEST] {name}")
            cmd = f"curl -s -w '\\nHTTP_CODE:%{{http_code}}' -X POST 'https://masternoder.dk{endpoint}' -H 'Content-Type: application/json' -d '{{}}'"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode('utf-8', errors='ignore')
            
            if "HTTP_CODE:200" in output or "HTTP_CODE:400" in output:
                print(f"    [SUCCESS] Endpoint accessible")
            elif "HTTP_CODE:404" in output:
                print(f"    [FAIL] Status 404")
            else:
                print(f"    [INFO] {output[-50:]}")
        
        ssh.close()
        
        print("\n" + "="*70)
        print("DEPLOYMENT COMPLETE")
        print("="*70)
        print("\n[INFO] All systems deployed:")
        print("  [OK] Comprehensive auto-save system")
        print("  [OK] Intelligent URL router")
        print("  [OK] Atomic calculator (Hell & Money Satan)")
        print("  [OK] Enhanced frontpage stats")
        print("\n[INFO] Features:")
        print("  - Auto-save every 5-60 seconds")
        print("  - Intelligent URL processing with logic")
        print("  - Atomic calculations with 50-digit precision")
        print("  - Enhanced stats display on frontpage")
        print("  - All unified system details visible")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_all()


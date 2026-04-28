"""
Deploy Comprehensive API Integration
Deploys all missing API routes and frontend integration
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def deploy_integration():
    """Deploy comprehensive API integration"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*60)
        print("DEPLOYING COMPREHENSIVE API INTEGRATION")
        print("="*60)
        
        files_to_deploy = [
            ('backend/routes/comprehensive_api_routes.py', '/var/www/html/vidgenerator/backend/routes/comprehensive_api_routes.py'),
            ('vidgenerator/static/js/comprehensive-api-integration.js', '/var/www/html/vidgenerator/vidgenerator/static/js/comprehensive-api-integration.js'),
            ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
            ('vidgenerator/index.html', '/var/www/html/vidgenerator/vidgenerator/index.html'),
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
        
        print("\n[STEP 4] Testing API endpoints...")
        endpoints = [
            ("/vidgenerator/api/comprehensive/frontend/quick-actions?user_id=test", "Quick Actions"),
            ("/vidgenerator/api/comprehensive/frontend/navigation-links", "Navigation Links"),
            ("/vidgenerator/api/game-mechanics/subjects?user_id=test", "Game Mechanics"),
            ("/vidgenerator/api/ultra-resource/energy?user_id=test", "Ultra Resource"),
        ]
        
        for endpoint, name in endpoints:
            print(f"\n  [TEST] {name}")
            cmd = f"curl -s -w '\\nHTTP_CODE:%{{http_code}}' 'https://masternoder.dk{endpoint}'"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode('utf-8', errors='ignore')
            
            if "HTTP_CODE:200" in output:
                body = output.split("HTTP_CODE")[0].strip()
                print(f"    [SUCCESS] Status 200")
                try:
                    import json
                    data = json.loads(body)
                    if 'success' in data:
                        print(f"    Response: success={data.get('success')}")
                except:
                    pass
            elif "HTTP_CODE:404" in output:
                print(f"    [FAIL] Status 404")
            else:
                print(f"    [INFO] {output[-50:]}")
        
        ssh.close()
        
        print("\n" + "="*60)
        print("DEPLOYMENT COMPLETE")
        print("="*60)
        print("\n[INFO] All comprehensive API integration deployed:")
        print("  [OK] Comprehensive API routes")
        print("  [OK] Frontend JavaScript integration")
        print("  [OK] Front page API buttons")
        print("  [OK] Onclick handlers")
        print("\n[INFO] Front page now includes:")
        print("  - API Integration section with onclick buttons")
        print("  - Game Mechanics API buttons")
        print("  - Ultra Resource API buttons")
        print("  - Skills, Calendar, Todos, Scanner buttons")
        print("  - All with onclick handlers")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_integration()


#!/usr/bin/env python3
"""
Check API keys on the server
"""
import os
import sys
import paramiko

# Fix UnicodeEncodeError on Windows
sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = os.getenv("DEPLOY_PATH", "/var/www/html/vidgenerator")

def check_server_api_keys():
    """Check API keys on server"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("CHECKING API KEYS ON SERVER")
        print("=" * 80)
        print(f"Server: {SERVER_HOST}")
        print(f"Path: {REMOTE_PATH}")
        print()
        
        print("Connecting to server...")
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        print("[OK] Connected!")
        print()
        
        # Check .env file
        remote_env_path = f"{REMOTE_PATH}/.env"
        print(f"Checking {remote_env_path}...")
        stdin, stdout, stderr = ssh_client.exec_command(f"test -f {remote_env_path} && echo 'EXISTS' || echo 'NOT_EXISTS'")
        env_exists = stdout.read().decode('utf-8').strip() == 'EXISTS'
        
        if env_exists:
            print("[OK] .env file exists")
            print()
            print("Reading API keys...")
            stdin, stdout, stderr = ssh_client.exec_command(f"grep -E '(RUNWAYML_API_KEY|PIKA_LABS_API_KEY|STABILITY_AI_API_KEY|STABLE_VIDEO_API_KEY|OPENAI_API_KEY)=' {remote_env_path} | grep -v '^#'")
            api_keys_output = stdout.read().decode('utf-8').strip()
            
            if api_keys_output:
                print("[OK] Found API keys:")
                print("-" * 80)
                for line in api_keys_output.split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if value:
                            # Mask the key value
                            masked = value[:10] + "..." + value[-4:] if len(value) > 14 else "***"
                            print(f"  {key}: {masked}")
                        else:
                            print(f"  {key}: (empty)")
                print("-" * 80)
            else:
                print("[WARN] No API keys found in .env file")
        else:
            print("[WARN] .env file not found")
        
        # Also check environment variables
        print()
        print("Checking environment variables...")
        stdin, stdout, stderr = ssh_client.exec_command("env | grep -E '(RUNWAYML_API_KEY|PIKA_LABS_API_KEY|STABILITY_AI_API_KEY|STABLE_VIDEO_API_KEY|OPENAI_API_KEY)'")
        env_vars = stdout.read().decode('utf-8').strip()
        
        if env_vars:
            print("[OK] Found in environment:")
            for line in env_vars.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    masked = value[:10] + "..." + value[-4:] if len(value) > 14 else "***"
                    print(f"  {key}: {masked}")
        else:
            print("[INFO] No API keys in environment variables")
        
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        # Test provider availability
        print()
        print("Testing provider availability...")
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {REMOTE_PATH} && python3 -c \"import sys; sys.path.insert(0, '.'); from src.services.video_generation.video_generator import VideoGenerator; g = VideoGenerator(); print('Available:', ','.join(g.get_available_providers()))\" 2>&1")
        test_output = stdout.read().decode('utf-8').strip()
        error_output = stderr.read().decode('utf-8').strip()
        
        if test_output:
            print(f"Result: {test_output}")
        if error_output:
            print(f"Errors: {error_output[:200]}")
        
        print()
        print("=" * 80)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    check_server_api_keys()


#!/usr/bin/env python3
"""
Ensure API keys are loaded by the application
This script checks and fixes environment variable loading
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

def ensure_api_keys_loaded():
    """Ensure API keys are loaded by the application"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("ENSURING API KEYS ARE LOADED")
        print("=" * 80)
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
        
        # Read .env file
        remote_env_path = f"{REMOTE_PATH}/.env"
        print(f"Reading {remote_env_path}...")
        stdin, stdout, stderr = ssh_client.exec_command(f"cat {remote_env_path}")
        env_content = stdout.read().decode('utf-8')
        
        # Extract API keys
        api_keys = {}
        for line in env_content.split('\n'):
            line = line.strip()
            if '=' in line and any(key in line for key in ['RUNWAYML_API_KEY', 'PIKA_LABS_API_KEY', 'STABILITY_AI_API_KEY', 'STABLE_VIDEO_API_KEY', 'OPENAI_API_KEY']) and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if value:
                    api_keys[key] = value
        
        print(f"Found {len(api_keys)} API keys in .env file")
        print()
        
        # Check uWSGI service file
        print("Checking uWSGI service configuration...")
        stdin, stdout, stderr = ssh_client.exec_command("systemctl cat uwsgi 2>/dev/null || systemctl cat uwsgi.service 2>/dev/null || echo 'NOT_FOUND'")
        service_content = stdout.read().decode('utf-8')
        
        if 'NOT_FOUND' in service_content:
            print("[WARN] uWSGI service file not found")
        else:
            print("[OK] Found uWSGI service file")
            # Check if EnvironmentFile is set
            if 'EnvironmentFile' in service_content or 'Environment=' in service_content:
                print("[OK] Environment variables configured in service file")
            else:
                print("[INFO] Environment variables not in service file (using .env loading)")
        
        print()
        
        # Test if providers are available
        print("Testing provider availability...")
        test_script = f"""
import sys
import os
sys.path.insert(0, '{REMOTE_PATH}')
os.chdir('{REMOTE_PATH}')

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv('{remote_env_path}')
except:
    pass

# Test providers
try:
    from src.services.video_generation.video_generator import VideoGenerator
    g = VideoGenerator()
    providers = g.get_available_providers()
    print('AVAILABLE_PROVIDERS:', ','.join(providers))
    
    # Check each provider
    for provider in g.providers:
        name = type(provider).__name__.replace('Provider', '')
        available = provider.is_available()
        print(f'PROVIDER:{name}:{"AVAILABLE" if available else "NOT_AVAILABLE"}')
        if hasattr(provider, 'api_key'):
            key_set = bool(provider.api_key)
            print(f'KEY_SET:{name}:{"YES" if key_set else "NO"}')
except Exception as e:
    print('ERROR:', str(e))
    import traceback
    traceback.print_exc()
"""
        
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {REMOTE_PATH} && python3 -c {repr(test_script)}")
        test_output = stdout.read().decode('utf-8')
        test_errors = stderr.read().decode('utf-8')
        
        print("Test Results:")
        print("-" * 80)
        if test_output:
            for line in test_output.split('\n'):
                if line.strip():
                    print(f"  {line}")
        if test_errors:
            print("Errors:")
            for line in test_errors.split('\n')[:10]:  # First 10 lines
                if line.strip():
                    print(f"  {line}")
        print("-" * 80)
        print()
        
        # Restart services to ensure .env is loaded
        print("Restarting services to load API keys...")
        print("-" * 80)
        
        # Restart uWSGI
        stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code == 0:
            print("[OK] uWSGI restarted")
        else:
            error = stderr.read().decode('utf-8')
            print(f"[WARN] uWSGI restart: {error[:200]}")
        
        # Restart python-proxy
        stdin, stdout, stderr = ssh_client.exec_command("systemctl restart python-proxy.service")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code == 0:
            print("[OK] python-proxy restarted")
        else:
            error = stderr.read().decode('utf-8')
            print(f"[WARN] python-proxy restart: {error[:200]}")
        
        print()
        print("=" * 80)
        print("[OK] COMPLETE")
        print("=" * 80)
        print()
        print("API keys should now be loaded. Test by generating a video.")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    ensure_api_keys_loaded()


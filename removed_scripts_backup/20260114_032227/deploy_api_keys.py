#!/usr/bin/env python3
"""
Deploy API keys to server automatically
No interactive prompts - uses local .env file
"""
import os
import sys
import paramiko
from pathlib import Path
from scp import SCPClient

def deploy_api_keys_to_server():
    """Deploy API keys from local .env to server"""
    
    SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
    USERNAME = os.getenv("DEPLOY_USER", "root")
    PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
    REMOTE_PATH = os.getenv("DEPLOY_PATH", "/var/www/html/vidgenerator")
    
    print("=" * 70)
    print("DEPLOY API KEYS TO SERVER")
    print("=" * 70)
    print()
    
    # Read local .env
    local_env = Path('.env')
    if not local_env.exists():
        print("Error: Local .env file not found.")
        return False
    
    print("Reading local .env file...")
    env_content = local_env.read_text()
    
    # Extract API keys
    api_keys = {}
    for line in env_content.split('\n'):
        line = line.strip()
        if '=' in line and any(key in line for key in ['API_KEY', 'OPENAI']) and not line.startswith('#'):
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            if value and key in ['RUNWAYML_API_KEY', 'PIKA_LABS_API_KEY', 'STABILITY_AI_API_KEY', 'STABLE_VIDEO_API_KEY', 'OPENAI_API_KEY']:
                api_keys[key] = value
    
    if not api_keys:
        print("No API keys found in local .env file.")
        return False
    
    print(f"Found {len(api_keys)} API keys:")
    for key in api_keys.keys():
        print(f"  - {key}")
    print()
    
    # Connect to server
    print(f"Connecting to {SERVER_HOST}...")
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh_client.connect(hostname=SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        print("[OK] Connected to server")
        
        # Read server .env
        remote_env_path = f"{REMOTE_PATH}/.env"
        stdin, stdout, stderr = ssh_client.exec_command(f"test -f {remote_env_path} && echo 'EXISTS' || echo 'NOT_EXISTS'")
        env_exists = stdout.read().decode('utf-8').strip() == 'EXISTS'
        
        if env_exists:
            print(f"Reading existing server .env file...")
            stdin, stdout, stderr = ssh_client.exec_command(f"cat {remote_env_path}")
            server_env_content = stdout.read().decode('utf-8')
        else:
            # Create from .env.example if it exists
            print("Server .env not found, checking for .env.example...")
            stdin, stdout, stderr = ssh_client.exec_command(f"test -f {REMOTE_PATH}/.env.example && cat {REMOTE_PATH}/.env.example || echo ''")
            server_env_content = stdout.read().decode('utf-8')
            if not server_env_content.strip():
                # Create minimal .env structure
                server_env_content = "# Environment Variables\n"
        
        # Update API keys in server .env
        lines = server_env_content.split('\n')
        updated_keys = set()
        
        print("Updating API keys...")
        for i, line in enumerate(lines):
            for key, value in api_keys.items():
                if line.startswith(f'{key}='):
                    lines[i] = f'{key}={value}'
                    updated_keys.add(key)
                    print(f"  [OK] Updated {key}")
        
        # Add missing keys
        for key, value in api_keys.items():
            if key not in updated_keys:
                lines.append(f'{key}={value}')
                print(f"  [OK] Added {key}")
        
        # Write updated .env to server using SCP
        updated_content = '\n'.join(lines)
        
        print()
        print("Uploading .env file to server...")
        
        # Use SCP to upload file
        scp = SCPClient(ssh_client.get_transport())
        try:
            # Create a temporary local file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp_file:
                tmp_file.write(updated_content)
                tmp_file_path = tmp_file.name
            
            # Upload via SCP
            scp.put(tmp_file_path, remote_env_path)
            
            # Clean up temp file
            os.unlink(tmp_file_path)
            
            print(f"[OK] Uploaded .env to {remote_env_path}")
        except Exception as e:
            print(f"Error with SCP: {e}")
            # Fallback: write directly via SFTP
            sftp = ssh_client.open_sftp()
            try:
                with sftp.open(remote_env_path, 'w') as remote_file:
                    remote_file.write(updated_content)
                print(f"[OK] Updated {remote_env_path} via SFTP")
            finally:
                sftp.close()
        finally:
            scp.close()
        
        # Set correct permissions
        print("Setting file permissions...")
        stdin, stdout, stderr = ssh_client.exec_command(f"chmod 600 {remote_env_path}")
        stdout.channel.recv_exit_status()
        print("[OK] Permissions set")
        
        # Restart services to load new environment variables
        print()
        print("Restarting Flask service to load new API keys...")
        stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi-vidgenerator.service")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("[OK] Flask service restarted")
        else:
            error = stderr.read().decode('utf-8')
            print(f"⚠ Warning: Service restart may have failed: {error[:200]}")
        
        print()
        print("=" * 70)
        print("[OK] API keys deployed to server successfully!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh_client.close()


if __name__ == '__main__':
    success = deploy_api_keys_to_server()
    sys.exit(0 if success else 1)


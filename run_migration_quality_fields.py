"""Run migration to add quality fields to documentaries table"""
import os
import sys
import paramiko

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

def run_migration():
    """Run the migration on the server"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 70)
        print("Running Database Migration")
        print("=" * 70)
        print(f"Connecting to {SERVER_HOST}...")
        
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        
        print("[OK] Connected!")
        print()
        
        # First, upload the migration script
        print("Uploading migration script...")
        sftp = ssh_client.open_sftp()
        
        local_migration = "migrations/add_quality_fields.py"
        remote_migration = f"{REMOTE_PATH}/migrations/add_quality_fields.py"
        
        if os.path.exists(local_migration):
            # Ensure remote directory exists
            stdin, stdout, stderr = ssh_client.exec_command(f"mkdir -p {REMOTE_PATH}/migrations")
            stdout.channel.recv_exit_status()
            
            sftp.put(local_migration, remote_migration)
            print(f"[OK] Uploaded migration script")
        else:
            print(f"[WARN] Migration script not found locally: {local_migration}")
        
        sftp.close()
        
        # Run the migration
        print()
        print("Running migration...")
        print("-" * 70)
        
        # Change to the vidgenerator directory and run the migration
        command = f"cd {REMOTE_PATH} && python3 migrations/add_quality_fields.py"
        
        stdin, stdout, stderr = ssh_client.exec_command(command)
        
        # Get output
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        error_output = stderr.read().decode('utf-8', errors='ignore')
        
        print(output)
        if error_output:
            print("Errors:")
            print(error_output)
        
        print("-" * 70)
        
        if exit_status == 0:
            print("[OK] Migration completed successfully!")
        else:
            print(f"[WARN] Migration exited with status {exit_status}")
            print("This might be okay if columns already exist.")
        
        print()
        print("=" * 70)
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh_client.close()
    
    return True

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)


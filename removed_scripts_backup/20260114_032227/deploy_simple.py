"""
Simple deployment - Step by step with error handling
"""
import subprocess
import sys
import os
import glob

# Configuration
REMOTE_HOST = "masternoder.dk"
REMOTE_USER = "root"
REMOTE_PATH = "/var/www/masternoder"

print("=" * 60)
print("Automatic Deployment to Ubuntu Server")
print("=" * 60)

# Find latest deployment package
packages = glob.glob("deployment_*.tar.gz")
if not packages:
    print("[ERROR] No deployment package found.")
    print("Run: python deploy_automatic.py")
    sys.exit(1)

package_name = max(packages, key=os.path.getctime)
package_size = os.path.getsize(package_name) / 1024
print(f"\n[INFO] Package: {os.path.basename(package_name)}")
print(f"[INFO] Size: {package_size:.2f} KB")

# Step 1: Upload
print("\n[STEP 1] Uploading package to server...")
print(f"Command: scp {os.path.basename(package_name)} {REMOTE_USER}@{REMOTE_HOST}:/tmp/")

try:
    result = subprocess.run(
        ["scp", package_name, f"{REMOTE_USER}@{REMOTE_HOST}:/tmp/"],
        check=True,
        capture_output=True,
        text=True,
        timeout=60
    )
    print("[SUCCESS] Package uploaded successfully!")
except FileNotFoundError:
    print("[ERROR] SCP command not found.")
    print("\nPlease install OpenSSH client or use manual upload:")
    print(f"scp {package_name} {REMOTE_USER}@{REMOTE_HOST}:/tmp/")
    sys.exit(1)
except subprocess.TimeoutExpired:
    print("[ERROR] Upload timed out. Check network connection.")
    sys.exit(1)
except subprocess.CalledProcessError as e:
    print(f"[ERROR] Upload failed!")
    print(f"Error: {e.stderr}")
    print("\nPossible issues:")
    print("1. SSH key not configured")
    print("2. Server not accessible")
    print("3. Authentication failed")
    print("\nTry manual upload:")
    print(f"scp {package_name} {REMOTE_USER}@{REMOTE_HOST}:/tmp/")
    sys.exit(1)

# Step 2: Extract and restart
print("\n[STEP 2] Extracting files and restarting service...")
package_basename = os.path.basename(package_name)

commands = [
    f"cd {REMOTE_PATH}",
    f"echo 'Extracting {package_basename}...'",
    f"tar -xzf /tmp/{package_basename}",
    "echo 'Files extracted successfully'",
    "echo 'Restarting service...'",
    "sudo systemctl restart masternoder",
    "sleep 3",
    "echo 'Checking service status...'",
    "sudo systemctl status masternoder --no-pager -l | head -20"
]

ssh_command = " && ".join(commands)
print(f"Executing on remote server...")

try:
    result = subprocess.run(
        ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", ssh_command],
        check=True,
        capture_output=True,
        text=True,
        timeout=120
    )
    print("[SUCCESS] Deployment completed!")
    print("\n" + "=" * 60)
    print("Service Output:")
    print("=" * 60)
    print(result.stdout)
    if result.stderr:
        print("\nWarnings/Errors:")
        print(result.stderr)
    print("\n" + "=" * 60)
    print("[SUCCESS] All done! Service should be running.")
    print("=" * 60)
except subprocess.TimeoutExpired:
    print("[ERROR] Deployment timed out.")
    print("Service may still be restarting. Check manually:")
    print(f"ssh {REMOTE_USER}@{REMOTE_HOST}")
    print("sudo systemctl status masternoder")
except subprocess.CalledProcessError as e:
    print(f"[ERROR] Deployment failed!")
    print(f"Error output: {e.stderr}")
    print(f"Standard output: {e.stdout}")
    print("\nManual deployment commands:")
    print(f"ssh {REMOTE_USER}@{REMOTE_HOST}")
    print(f"cd {REMOTE_PATH}")
    print(f"tar -xzf /tmp/{package_basename}")
    print("sudo systemctl restart masternoder")
    sys.exit(1)


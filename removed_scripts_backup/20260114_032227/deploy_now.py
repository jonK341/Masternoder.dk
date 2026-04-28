"""
Quick deployment - Upload and deploy package automatically
"""
import subprocess
import sys
import os
import glob

# Configuration
REMOTE_HOST = "masternoder.dk"
REMOTE_USER = "root"
REMOTE_PATH = "/var/www/masternoder"

# Find latest deployment package
packages = glob.glob("deployment_*.tar.gz")
if not packages:
    print("[ERROR] No deployment package found. Run deploy_automatic.py first.")
    sys.exit(1)

package_name = max(packages, key=os.path.getctime)
print(f"[INFO] Using package: {package_name}")

# Step 1: Upload
print("\n[STEP 1] Uploading package...")
try:
    result = subprocess.run(
        ["scp", package_name, f"{REMOTE_USER}@{REMOTE_HOST}:/tmp/"],
        check=True,
        capture_output=True,
        text=True
    )
    print("[SUCCESS] Package uploaded!")
except FileNotFoundError:
    print("[ERROR] SCP not found. Install OpenSSH client.")
    print(f"\nManual upload:")
    print(f"scp {package_name} {REMOTE_USER}@{REMOTE_HOST}:/tmp/")
    sys.exit(1)
except subprocess.CalledProcessError as e:
    print(f"[ERROR] Upload failed: {e.stderr}")
    sys.exit(1)

# Step 2: Extract and restart
print("\n[STEP 2] Extracting and restarting service...")
commands = [
    f"cd {REMOTE_PATH}",
    f"tar -xzf /tmp/{os.path.basename(package_name)}",
    "sudo systemctl restart masternoder",
    "sleep 2",
    "sudo systemctl status masternoder --no-pager -l"
]

ssh_command = " && ".join(commands)

try:
    result = subprocess.run(
        ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", ssh_command],
        check=True,
        capture_output=True,
        text=True
    )
    print("[SUCCESS] Service restarted!")
    print("\n" + "="*60)
    print("Service Status:")
    print("="*60)
    print(result.stdout)
    print("\n[SUCCESS] Deployment complete!")
except subprocess.CalledProcessError as e:
    print(f"[ERROR] Deployment failed: {e.stderr}")
    print("\nManual commands:")
    print(f"ssh {REMOTE_USER}@{REMOTE_HOST}")
    print(f"cd {REMOTE_PATH}")
    print(f"tar -xzf /tmp/{os.path.basename(package_name)}")
    print("sudo systemctl restart masternoder")
    sys.exit(1)


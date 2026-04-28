"""
Final Queue Deployment - Simple and Direct
"""
import os
import tarfile
import subprocess
import sys
from datetime import datetime

REMOTE_HOST = "masternoder.dk"
REMOTE_USER = "root"
REMOTE_PATH = "/var/www/masternoder"

FILES = [
    "src/db/models_agent.py",
    "backend/services/agent_system.py",
    "backend/routes/agent_routes.py",
    "backend/services/unified_point_connector.py",
    "backend/routes/unified_point_connector_routes.py",
    "backend/services/mind_energy_system.py",
    "backend/routes/mind_energy_routes.py",
    "backend/services/video_generation_enhancer.py",
    "backend/routes/profile_routes.py",
    "backend/routes/generator.py",
    "backend/register_blueprints.py",
    "vidgenerator/profile/index.html",
    "vidgenerator/generator/index.html",
    "vidgenerator/service-worker.js",
]

print("=" * 70)
print("FINAL DEPLOYMENT QUEUE")
print("=" * 70)

# Check files
print("\n[1/4] Checking files...")
missing = [f for f in FILES if not os.path.exists(f)]
if missing:
    print(f"ERROR: {len(missing)} files missing")
    for f in missing:
        print(f"  - {f}")
    sys.exit(1)
print(f"OK: All {len(FILES)} files found")

# Create package
print("\n[2/4] Creating package...")
pkg_name = f"deployment_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
with tarfile.open(pkg_name, "w:gz") as tar:
    for f in FILES:
        tar.add(f)
print(f"OK: {pkg_name} created ({os.path.getsize(pkg_name)/1024:.1f} KB)")

# Upload
print(f"\n[3/4] Uploading to {REMOTE_HOST}...")
print("(This may prompt for password)")
try:
    subprocess.run(["scp", pkg_name, f"{REMOTE_USER}@{REMOTE_HOST}:/tmp/"], check=True)
    print("OK: Upload successful")
except Exception as e:
    print(f"ERROR: Upload failed - {e}")
    print(f"\nManual upload:")
    print(f"  scp {pkg_name} {REMOTE_USER}@{REMOTE_HOST}:/tmp/")
    sys.exit(1)

# Deploy
print(f"\n[4/4] Deploying on server...")
cmd = f"cd {REMOTE_PATH} && tar -xzf /tmp/{os.path.basename(pkg_name)} && sudo systemctl restart masternoder && echo 'DEPLOYMENT COMPLETE'"
try:
    result = subprocess.run(["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", cmd], 
                          capture_output=True, text=True, timeout=120, check=True)
    print("OK: Deployment successful")
    print("\nService output:")
    print(result.stdout)
except Exception as e:
    print(f"ERROR: Deployment failed - {e}")
    print(f"\nManual deploy:")
    print(f"  ssh {REMOTE_USER}@{REMOTE_HOST}")
    print(f"  cd {REMOTE_PATH}")
    print(f"  tar -xzf /tmp/{os.path.basename(pkg_name)}")
    print(f"  sudo systemctl restart masternoder")
    sys.exit(1)

print("\n" + "=" * 70)
print("DEPLOYMENT QUEUE COMPLETE!")
print("=" * 70)
print("\nDeployed:")
print("  - Agent System (Top100/Top50/Top25/Top10)")
print("  - Giga Calendar (10 levels)")
print("  - Mind Energy System")
print("  - Unified Point Connector")
print("  - Video Generation Enhancer")
print("  - Profile Enhancements")
print("  - Service Worker Coordination")
print("\nAll systems are live!")


#!/usr/bin/env python3
"""
Deploy PayPal and shop updates to production.
Uploads PayPal, shop, account resolution, and related files, then restarts services.
"""
import paramiko
import os
import sys
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.environ.get('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_BASE = "/var/www/html"

# PayPal + shop + account control files + .env
FILES_TO_DEPLOY = [
    ".env",
    "backend/register_blueprints.py",
    "backend/routes/paypal_routes.py",
    "backend/routes/shop_routes.py",
    "backend/services/paypal_service.py",
    "backend/services/purchase_notification_service.py",
    "backend/services/account_resolution_service.py",
    "backend/routes/user_profile_routes.py",
    "backend/services/user_onboarding.py",
    "src/app/__init__.py",
    "vidgenerator/shop/index.html",
    "vidgenerator/profile/index.html",
    "vidgenerator/generator/index.html",
    "vidgenerator/static/css/navigation-toolbar.css",
    "vidgenerator/game/index.html",
]


def deploy_file(ssh, sftp, local_path: str) -> bool:
    """Deploy single file. Returns True on success."""
    if not os.path.exists(local_path):
        print(f"  [SKIP] {local_path} (not found)")
        return False
    remote_path = f"{REMOTE_BASE}/{local_path.replace(os.sep, '/')}"
    remote_dir = os.path.dirname(remote_path)
    try:
        ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
        with open(local_path, 'rb') as f:
            content = f.read()
        with sftp.open(remote_path, 'wb') as f:
            f.write(content)
        print(f"  [OK] {local_path}")
        return True
    except Exception as e:
        print(f"  [ERROR] {local_path}: {e}")
        return False


def main():
    print("=" * 70)
    print("DEPLOY PAYPAL & SHOP TO PRODUCTION")
    print("=" * 70)
    print()

    # Ensure we're in project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)

    try:
        print("[1/5] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("  [OK] Connected")
        print()

        print("[2/5] Deploying files...")
        deployed = 0
        for local_path in FILES_TO_DEPLOY:
            if deploy_file(ssh, sftp, local_path):
                deployed += 1
        sftp.close()
        print(f"  [SUMMARY] {deployed}/{len(FILES_TO_DEPLOY)} files deployed")
        print()

        print("[3/5] Clearing Python cache...")
        ssh.exec_command("find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        ssh.exec_command("find /var/www/html -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()

        print("[4/5] Restarting services...")
        for service in ['uwsgi', 'uwsgi-vidgenerator', 'python-proxy']:
            ssh.exec_command(f"systemctl stop {service} 2>&1", timeout=10)
        time.sleep(3)
        for service in ['uwsgi', 'uwsgi-vidgenerator', 'python-proxy']:
            ssh.exec_command(f"systemctl start {service} 2>&1", timeout=10)
        time.sleep(8)
        print("  [OK] Services restarted")
        print()

        print("[5/5] Verifying...")
        for service in ['uwsgi', 'uwsgi-vidgenerator', 'python-proxy']:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service} 2>&1", timeout=5)
            status = stdout.read().decode().strip()
            print(f"  {service}: {status}")
        print()

        # Test PayPal endpoint
        print("Testing PayPal endpoint...")
        stdin, stdout, stderr = ssh.exec_command(
            "curl -s -o /dev/null -w '%{http_code}' -X POST https://masternoder.dk/vidgenerator/api/paypal/create-order "
            "-H 'Content-Type: application/json' -d '{\"amount\":\"0\",\"user_id\":\"test\"}' 2>&1",
            timeout=10
        )
        code = stdout.read().decode().strip()
        if code == "400":
            print("  [OK] PayPal create-order responds (400 = expected for invalid amount)")
        elif code == "200":
            print("  [OK] PayPal endpoint responds")
        else:
            print(f"  [INFO] PayPal endpoint returned: {code}")

        ssh.close()

        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("PayPal & shop are live at: https://masternoder.dk/vidgenerator/shop")
        print("Ensure .env on server has PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_MODE=live")
        print()
        return True

    except Exception as e:
        print(f"\n[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

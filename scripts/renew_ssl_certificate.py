#!/usr/bin/env python3
"""Renew SSL certificate using Certbot on the remote server."""
import os
import sys
import time

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def _sh(ssh, cmd, timeout=60):
    """Execute command and return stdout, stderr."""
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    exit_code = stdout.channel.recv_exit_status()
    return out, err, exit_code


def main():
    import paramiko
    
    print("=" * 70)
    print("SSL Certificate Renewal")
    print("=" * 70)
    print(f"Connecting to {SERVER_HOST}...")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    
    try:
        # Step 0: Check and fix certbot installation
        print()
        print("[0/6] Checking certbot installation...")
        out, err, exit_code = _sh(ssh, "which certbot 2>&1", timeout=10)
        certbot_path = out.strip() if exit_code == 0 else None
        
        # Check if certbot works
        out_test, err_test, exit_code_test = _sh(ssh, "certbot --version 2>&1", timeout=10)
        certbot_broken = exit_code_test != 0
        
        # Check if it's a snap issue or Python dependency issue
        if certbot_broken:
            error_msg = (out_test + err_test).lower()
            is_snap_issue = "snap" in error_msg or "missing file" in error_msg
            is_python_issue = "attributeerror" in error_msg or "import" in error_msg or "openssl" in error_msg
            
            if is_snap_issue:
                print("  [WARN] Certbot snap installation appears broken")
                print("  Attempting to fix or use apt-installed version...")
                
                # Try to use /usr/bin/certbot (apt version)
                out_apt, err_apt, exit_code_apt = _sh(ssh, "/usr/bin/certbot --version 2>&1", timeout=10)
                if exit_code_apt == 0:
                    print("  [OK] Using apt-installed certbot at /usr/bin/certbot")
                    certbot_path = "/usr/bin/certbot"
                else:
                    print("  [INFO] Fixing certbot installation...")
                    # Try to fix snap first
                    print("    Attempting to fix snap certbot...")
                out_snap_fix, err_snap_fix, exit_code_snap_fix = _sh(
                    ssh,
                    "snap remove certbot 2>&1; snap install --classic certbot 2>&1",
                    timeout=120
                )
                if exit_code_snap_fix == 0:
                    print("  [OK] Snap certbot reinstalled")
                    certbot_path = "certbot"
                else:
                    print("    Snap fix failed, trying apt installation...")
                    # Fix Python dependencies first
                    print("    Fixing Python OpenSSL dependencies...")
                    out_fix_deps, err_fix_deps, exit_code_fix_deps = _sh(
                        ssh,
                        "apt-get update && apt-get install -y --reinstall python3-pyopenssl python3-cryptography python3-openssl 2>&1",
                        timeout=120
                    )
                    # Update packages and install certbot via apt
                    out_install, err_install, exit_code_install = _sh(
                        ssh,
                        "apt-get install -y --reinstall certbot python3-certbot-nginx 2>&1",
                        timeout=180
                    )
                    if exit_code_install == 0:
                        print("  [OK] Certbot installed via apt")
                        certbot_path = "/usr/bin/certbot"
                        # Test if it works now
                        out_test, err_test, exit_code_test = _sh(ssh, f"{certbot_path} --version 2>&1", timeout=10)
                        if exit_code_test != 0:
                            print("  [WARN] Certbot still has issues, trying pip upgrade...")
                            out_pip, err_pip, exit_code_pip = _sh(
                                ssh,
                                "pip3 install --upgrade --force-reinstall pyopenssl cryptography 2>&1",
                                timeout=120
                            )
                    else:
                        print(f"  [ERROR] Failed to install certbot: {err_install}")
                        print("  Trying alternative: using certbot via python3 -m certbot")
                        certbot_path = "python3 -m certbot"
            elif is_python_issue:
                print("  [WARN] Certbot has Python dependency issues")
                print("  Fixing Python OpenSSL dependencies...")
                
                # Fix Python dependencies
                print("    Upgrading Python OpenSSL packages...")
                out_fix, err_fix, exit_code_fix = _sh(
                    ssh,
                    "apt-get update && apt-get install -y --reinstall python3-pyopenssl python3-cryptography python3-openssl python3-certbot python3-certbot-nginx 2>&1",
                    timeout=180
                )
                
                # Also try pip upgrade
                print("    Upgrading via pip...")
                out_pip, err_pip, exit_code_pip = _sh(
                    ssh,
                    "pip3 install --upgrade --force-reinstall pyopenssl cryptography certbot 2>&1",
                    timeout=120
                )
                
                # Test if certbot works now
                out_test2, err_test2, exit_code_test2 = _sh(ssh, "certbot --version 2>&1", timeout=10)
                if exit_code_test2 == 0:
                    print("  [OK] Certbot fixed and working")
                    certbot_path = "certbot"
                else:
                    print("  [WARN] Certbot still broken, will try snap...")
                    out_snap, err_snap, exit_code_snap = _sh(
                        ssh,
                        "snap remove certbot 2>&1; snap install --classic certbot 2>&1",
                        timeout=120
                    )
                    if exit_code_snap == 0:
                        certbot_path = "certbot"
                    else:
                        certbot_path = "/usr/bin/certbot"  # Try anyway
            else:
                print(f"  [WARN] Certbot error: {out_test[:200]}")
                certbot_path = certbot_path or "certbot"
        else:
            certbot_path = certbot_path or "certbot"
            print(f"  [OK] Using certbot at: {certbot_path}")
        
        # Verify certbot works before proceeding
        print("  Verifying certbot works...")
        out_verify, err_verify, exit_code_verify = _sh(ssh, f"{certbot_path} --version 2>&1", timeout=10)
        if exit_code_verify != 0:
            print(f"  [ERROR] Certbot still not working: {out_verify[:200]}")
            print("  Attempting to use snap certbot as last resort...")
            out_snap_last, err_snap_last, exit_code_snap_last = _sh(
                ssh,
                "snap remove certbot 2>&1; snap install --classic certbot 2>&1",
                timeout=120
            )
            certbot_path = "certbot"
        
        # Step 1: Check current certificate expiration
        print()
        print("[1/6] Checking current certificate expiration...")
        out, err, exit_code = _sh(ssh, f"{certbot_path} certificates 2>&1", timeout=30)
        if exit_code == 0:
            print(out)
        else:
            print(f"Warning: Could not list certificates: {err}")
        
        # Check expiration date specifically
        print()
        print("[2/6] Checking certificate expiration date...")
        out, err, exit_code = _sh(
            ssh,
            "openssl x509 -enddate -noout -in /etc/letsencrypt/live/masternoder.dk/cert.pem 2>&1",
            timeout=30
        )
        if exit_code == 0:
            print(f"Certificate expiration: {out}")
        else:
            print(f"Warning: Could not check expiration: {err}")
        
        # Step 2: Test nginx config before renewal
        print()
        print("[3/6] Testing nginx configuration...")
        out, err, exit_code = _sh(ssh, "nginx -t 2>&1", timeout=30)
        if exit_code == 0:
            print("  [OK] Nginx config is valid")
        else:
            print(f"  [WARN] Nginx config test failed:")
            print(f"    {out}")
            print(f"    {err}")
            print("  Continuing anyway...")
        
        # Step 3: Renew certificate
        print()
        print("[4/6] Renewing SSL certificate...")
        print(f"  Running: {certbot_path} renew --non-interactive")
        
        # Try renewal with the certbot path
        renewal_cmd = f"{certbot_path} renew --non-interactive 2>&1"
        out, err, exit_code = _sh(ssh, renewal_cmd, timeout=120)
        
        if exit_code == 0:
            print("  [OK] Certificate renewal completed")
            if out:
                print(f"  Output: {out[:500]}")  # Show first 500 chars
        else:
            print(f"  [WARN] Standard renewal failed (exit code: {exit_code})")
            print(f"  Output: {out[:300]}")
            print(f"  Error: {err[:300]}")
            print()
            
            # Try alternative: use certonly to manually renew
            print("  Trying alternative renewal method...")
            print("  Running: certbot certonly --nginx --force-renewal -d masternoder.dk -d www.masternoder.dk --non-interactive")
            out2, err2, exit_code2 = _sh(
                ssh,
                f"{certbot_path} certonly --nginx --force-renewal -d masternoder.dk -d www.masternoder.dk --non-interactive --agree-tos 2>&1",
                timeout=180
            )
            if exit_code2 == 0:
                print("  [OK] Alternative renewal succeeded")
                out = out2
            else:
                print(f"  [ERROR] Alternative renewal also failed!")
                print(f"  Exit code: {exit_code2}")
                print(f"  Output: {out2[:500]}")
                print(f"  Error: {err2[:500]}")
                print()
                print("  [INFO] You may need to manually SSH into the server and run:")
                print("    certbot renew --force-renewal")
                print("  Or:")
                print("    certbot certonly --nginx --force-renewal -d masternoder.dk -d www.masternoder.dk")
                sys.exit(1)
        
        # Step 4: Reload nginx to use new certificate
        print()
        print("[5/6] Reloading nginx to use new certificate...")
        out, err, exit_code = _sh(ssh, "systemctl reload nginx 2>&1", timeout=30)
        if exit_code == 0:
            print("  [OK] Nginx reloaded successfully")
        else:
            print(f"  [WARN] Nginx reload had issues:")
            print(f"    {out}")
            print(f"    {err}")
            print("  Trying restart instead...")
            out2, err2, exit_code2 = _sh(ssh, "systemctl restart nginx 2>&1", timeout=30)
            if exit_code2 == 0:
                print("  [OK] Nginx restarted successfully")
            else:
                print(f"  [ERROR] Nginx restart failed!")
                print(f"    {out2}")
                print(f"    {err2}")
        
        # Step 5: Verify new certificate expiration
        print()
        print("Verifying new certificate expiration...")
        out, err, exit_code = _sh(
            ssh,
            "openssl x509 -enddate -noout -in /etc/letsencrypt/live/masternoder.dk/cert.pem 2>&1",
            timeout=30
        )
        if exit_code == 0:
            print(f"New certificate expiration: {out}")
        else:
            print(f"Warning: Could not verify new expiration: {err}")
        
        print()
        print("=" * 70)
        print("Certificate renewal complete!")
        print("=" * 70)
        print()
        print("Test your site:")
        print(f"  https://{SERVER_HOST}")
        print()
        print("Note: Certbot should auto-renew certificates in the future.")
        print(f"Check auto-renewal status: {certbot_path} renew --dry-run")
        print()
        
        sys.exit(0)
        
    except Exception as e:
        print(f"[ERROR] Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        ssh.close()


if __name__ == "__main__":
    main()

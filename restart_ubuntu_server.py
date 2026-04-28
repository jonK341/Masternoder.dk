#!/usr/bin/env python3
"""
Restart Ubuntu server and verify dashboard route after restart
"""
import os
import sys
import paramiko
import time
import requests

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
BASE_URL = "https://masternoder.dk"

def restart_server(ssh_client):
    """Restart the Ubuntu server"""
    print("=" * 70)
    print("RESTARTING UBUNTU SERVER")
    print("=" * 70)
    print("WARNING: This will restart the entire server!")
    print("Server will be unavailable for 1-2 minutes during restart.")
    print()
    
    try:
        print("Initiating server restart...")
        # Use nohup to keep command running after SSH disconnects
        stdin, stdout, stderr = ssh_client.exec_command("nohup reboot &")
        
        print("[OK] Reboot command sent")
        print("\nServer restart initiated. Script will wait for HTTPS to respond (typically 1–3 min).")
        print("(SSH connection will be lost - this is normal)")
        
        return True
    except Exception as e:
        print(f"[ERROR] Failed to restart server: {str(e)}")
        return False

def wait_for_server(min_wait=50, max_wait=240, required_ok=3):
    """Wait for server to come back online. Requires multiple consecutive OK responses after a minimum wait."""
    print("\n" + "=" * 70)
    print("WAITING FOR SERVER TO COME BACK ONLINE")
    print("=" * 70)
    print(f"  (minimum {min_wait}s boot time, then {required_ok} consecutive OK responses)")
    
    ok_count = 0
    for i in range(max_wait):
        try:
            response = requests.get(f"{BASE_URL}/vidgenerator/", timeout=8)
            if response.status_code in [200, 404]:
                if i >= min_wait:
                    ok_count += 1
                    if ok_count >= required_ok:
                        print(f"[OK] Server is back online after {i+1} seconds (HTTPS responding)")
                        return True
                else:
                    ok_count = 0  # reset until min_wait passed
            else:
                ok_count = 0
        except Exception:
            ok_count = 0
        
        if (i + 1) % 15 == 0:
            print(f"  Waiting... ({i+1}/{max_wait} s, need {min_wait}s min then {required_ok} OK)")
        time.sleep(1)
    
    print(f"[WARN] Server did not respond within {max_wait} seconds")
    return False

def check_dashboard_after_restart():
    """Check dashboard route after server restart"""
    print("\n" + "=" * 70)
    print("CHECKING DASHBOARD ROUTE AFTER RESTART")
    print("=" * 70)
    
    dashboard_urls = [
        f"{BASE_URL}/vidgenerator/dashboard",
        f"{BASE_URL}/vidgenerator/dashboard/",
        f"{BASE_URL}/vidgenerator/dashboard/index.html",
    ]
    
    results = {}
    for url in dashboard_urls:
        try:
            print(f"\nTesting: {url}")
            response = requests.get(url, timeout=10, allow_redirects=True)
            status_code = response.status_code
            results[url] = status_code
            
            if status_code == 200:
                print(f"[✅ SUCCESS] Status: {status_code} - Dashboard is working!")
            elif status_code == 404:
                print(f"[❌ FAILED] Status: {status_code} - Still returning 404")
            elif status_code == 500:
                print(f"[⚠️ ERROR] Status: {status_code} - Server error")
            else:
                print(f"[?] Status: {status_code} - Unexpected status")
        except Exception as e:
            err_str = str(e)
            if "10061" in err_str or "Connection refused" in err_str or "actively refused" in err_str:
                print(f"[ERROR] Connection refused (port 443) - server or nginx may still be starting")
            else:
                print(f"[ERROR] Request failed: {err_str[:120]}")
            results[url] = None
    
    return results

def main():
    """Main function"""
    print("=" * 70)
    print("UBUNTU SERVER RESTART & DASHBOARD VERIFICATION")
    print("=" * 70)
    print(f"Server: {SERVER_HOST}")
    print(f"Base URL: {BASE_URL}")
    print()
    
    # Confirm restart
    print("⚠️  WARNING: This script will restart the entire Ubuntu server!")
    print("   This will cause downtime (1-2 minutes)")
    print("   All services will be restarted")
    print()
    response = input("Continue with server restart? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("Restart cancelled.")
        return False
    
    ssh_client = None
    try:
        print("\nConnecting to server...")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        print("[OK] Connected!")
        print()
        
        # Restart server
        restart_server(ssh_client)
        
        # Close connection (it will be lost anyway)
        ssh_client.close()
        ssh_client = None
        
        # Wait for server to come back (min 50s + 3 OKs, then extra for nginx/uWSGI)
        if wait_for_server():
            print("\nWaiting 60 seconds for nginx and app services to start...")
            time.sleep(60)
            
            # Check dashboard
            results = check_dashboard_after_restart()
            
            # Summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            
            working = sum(1 for status in results.values() if status == 200)
            total = len(results)
            
            if working > 0:
                print(f"✅ SUCCESS: {working}/{total} dashboard URLs are working after restart!")
            else:
                all_refused = all(v is None for v in results.values())
                if all_refused:
                    print(f"❌ Connection refused to all URLs (0/{total} reached)")
                    print("\nHTTPS/nginx may still be starting after reboot. Try in 2–3 minutes:")
                    print("  curl -I https://masternoder.dk/vidgenerator/")
                    print("Or from this machine: python scripts/apply_updates.py  (restarts services)")
                else:
                    print(f"❌ Dashboard not OK: 0/{total} returned 200")
                    print("\nIf you see 404 or 500, the issue is in Apache/uWSGI or Flask routing.")
                    print("Next steps: check nginx/Apache config, uWSGI, and server logs.")
        
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Operation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if ssh_client:
            try:
                ssh_client.close()
            except:
                pass

if __name__ == "__main__":
    main()


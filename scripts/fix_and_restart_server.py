#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix and Restart Server - Check logs, fix issues, and restart services
"""
import paramiko
import os
import sys
import time
from datetime import datetime

# Fix Windows encoding issues
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def print_success(text):
    print(f"[OK] {text}")

def print_error(text):
    print(f"[ERROR] {text}")

def print_info(text):
    print(f"[INFO] {text}")

def check_logs(ssh):
    """Check recent error logs"""
    print("\n" + "=" * 70)
    print("CHECKING ERROR LOGS".center(70))
    print("=" * 70 + "\n")
    
    try:
        # Check Flask/uWSGI logs
        log_commands = [
            ("uWSGI error log", "tail -50 /var/log/uwsgi/error.log 2>&1 || echo 'No uwsgi error log'"),
            ("Python proxy log", "journalctl -u python-proxy.service -n 50 --no-pager 2>&1 || echo 'No python-proxy log'"),
            ("Systemd Flask log", "journalctl -u 'vidgenerator*' -n 30 --no-pager 2>&1 || echo 'No vidgenerator service log'"),
            ("Recent Python errors", "find /var/www/html/vidgenerator -name '*.log' -type f -exec tail -20 {} \\; 2>&1 | head -50 || echo 'No log files found'"),
        ]
        
        for name, cmd in log_commands:
            print_info(f"Checking {name}...")
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            output = stdout.read().decode('utf-8', errors='replace')
            if output.strip() and 'No' not in output[:20]:
                print(f"  {output[:500]}")
            else:
                print(f"  (No relevant log found)")
            print()
        
    except Exception as e:
        print_error(f"Could not check logs: {str(e)}")

def check_imports(ssh):
    """Check if new modules can be imported"""
    print("\n" + "=" * 70)
    print("CHECKING MODULE IMPORTS".center(70))
    print("=" * 70 + "\n")
    
    test_imports = [
        "from backend.services.enhanced_click_activity import EnhancedClickActivity",
        "from backend.services.trophy_system import TrophySystem",
        "from backend.services.system_history import SystemHistory",
        "from backend.routes.enhanced_features_routes import enhanced_features_bp",
    ]
    
    for import_cmd in test_imports:
        try:
            cmd = f"cd /var/www/html/vidgenerator && python3 -c '{import_cmd}' 2>&1"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            output = stdout.read().decode('utf-8', errors='replace')
            error = stderr.read().decode('utf-8', errors='replace')
            
            if error.strip() and 'Error' in error:
                print_error(f"{import_cmd.split()[-1]}: {error[:200]}")
            else:
                print_success(f"{import_cmd.split()[-1]}: OK")
        except Exception as e:
            print_error(f"Import check failed: {str(e)}")

def restart_services_properly(ssh):
    """Restart services with proper error handling"""
    print("\n" + "=" * 70)
    print("RESTARTING SERVICES".center(70))
    print("=" * 70 + "\n")
    
    # Find all Flask/uWSGI related services
    try:
        stdin, stdout, stderr = ssh.exec_command(
            "systemctl list-units --type=service --state=running,failed,activating | grep -iE '(flask|uwsgi|python-proxy|vidgenerator)' | awk '{print $1}'",
            timeout=10
        )
        services = [s.strip() for s in stdout.read().decode('utf-8', errors='replace').split('\n') if s.strip()]
        
        if not services:
            # Try common service names
            services = ['python-proxy.service', 'uwsgi-vidgenerator.service', 'vidgenerator-flask.service']
    except:
        services = ['python-proxy.service', 'uwsgi-vidgenerator.service']
    
    print_info(f"Found {len(services)} service(s) to restart")
    
    # Stop services
    print_info("Stopping services...")
    for service in services:
        try:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl stop {service} 2>&1", timeout=10)
            stdout.read()
            time.sleep(1)
        except:
            pass
    
    time.sleep(3)
    
    # Clear cache again
    print_info("Clearing cache...")
    ssh.exec_command("find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true", timeout=30)
    ssh.exec_command("find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
    
    # Start services
    print_info("Starting services...")
    for service in services:
        try:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl start {service} 2>&1", timeout=10)
            output = stdout.read().decode('utf-8', errors='replace')
            error = stderr.read().decode('utf-8', errors='replace')
            if error.strip():
                print_info(f"{service}: {error[:100]}")
        except Exception as e:
            print_error(f"{service}: {str(e)}")
    
    time.sleep(5)
    
    # Verify
    print_info("Verifying services...")
    for service in services:
        try:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service} 2>&1", timeout=5)
            status = stdout.read().decode('utf-8', errors='replace').strip()
            if 'active' in status.lower():
                print_success(f"{service}: Running")
            else:
                print_info(f"{service}: {status}")
        except:
            pass

def main():
    print("\n" + "=" * 70)
    print("FIX AND RESTART SERVER".center(70))
    print("=" * 70)
    print(f"Server: {SERVER_HOST}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    ssh = None
    try:
        print_info("Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print_success("Connected to server")
        
        # Step 1: Check logs for errors
        check_logs(ssh)
        
        # Step 2: Check if imports work
        check_imports(ssh)
        
        # Step 3: Restart services properly
        restart_services_properly(ssh)
        
        # Step 4: Wait and test
        print("\n" + "=" * 70)
        print("WAITING FOR SERVICES TO START".center(70))
        print("=" * 70 + "\n")
        print_info("Waiting 10 seconds for services to fully start...")
        time.sleep(10)
        
        # Test endpoint
        try:
            import importlib
            requests = importlib.import_module('requests')
            response = requests.get(f"https://{SERVER_HOST}/vidgenerator", timeout=10, verify=False)
            if response.status_code == 200:
                print_success(f"Server is responding! Status: {response.status_code}")
            elif response.status_code == 500:
                print_error(f"Server error (500) - check logs above for details")
            else:
                print_info(f"Server responded with status: {response.status_code}")
        except ImportError:
            print_info("requests module not available - skipping endpoint test")
        except Exception as e:
            print_info(f"Endpoint test: {str(e)[:100]}")
        
        print("\n" + "=" * 70)
        print("COMPLETE".center(70))
        print("=" * 70 + "\n")
        print_info(f"Live URL: https://{SERVER_HOST}/vidgenerator")
        print_info("If issues persist, check the error logs above")
        
        return 0
        
    except Exception as e:
        print_error(f"Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if ssh:
            ssh.close()

if __name__ == '__main__':
    sys.exit(main())

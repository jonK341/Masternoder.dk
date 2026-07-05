#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnose why code changes aren't taking effect
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def diagnose():
    """Diagnose reload issues"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        print("=" * 80)
        print("DIAGNOSING RELOAD ISSUE")
        print("=" * 80)
        print()
        
        # Check 1: Find all Python processes
        print("[1] Finding all Python/uWSGI processes...")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep -E 'python|uwsgi' | grep -v grep")
        processes = stdout.read().decode()
        print(processes)
        print()
        
        # Check 2: Find all battle.py files
        print("[2] Finding all battle.py files...")
        stdin, stdout, stderr = ssh.exec_command("find /var/www -name 'battle.py' -type f 2>/dev/null")
        battle_files = stdout.read().decode()
        print(battle_files)
        print()
        
        # Check 3: Check uWSGI configuration
        print("[3] Checking uWSGI configuration...")
        stdin, stdout, stderr = ssh.exec_command("systemctl cat uwsgi-vidgenerator 2>&1 | head -30")
        uwsgi_config = stdout.read().decode()
        print(uwsgi_config)
        print()
        
        # Check 4: Check if there are multiple uWSGI instances
        print("[4] Checking uWSGI instances...")
        stdin, stdout, stderr = ssh.exec_command("systemctl list-units | grep uwsgi")
        uwsgi_units = stdout.read().decode()
        print(uwsgi_units)
        print()
        
        # Check 5: Check Python path in running process
        print("[5] Checking Python path in uWSGI process...")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep uwsgi | grep -v grep | head -1 | awk '{print $2}' | xargs -I {} cat /proc/{}/environ 2>/dev/null | tr '\\0' '\\n' | grep PYTHON")
        python_env = stdout.read().decode()
        if python_env:
            print(python_env)
        else:
            print("  [INFO] No PYTHON env vars found")
        print()
        
        # Check 6: Check if code is being imported from a different location
        print("[6] Checking where battle module is imported from...")
        stdin, stdout, stderr = ssh.exec_command("python3 -c 'import sys; sys.path.insert(0, \"/var/www/html\"); from backend.routes import battle; print(battle.__file__)' 2>&1")
        import_path = stdout.read().decode()
        print(import_path)
        print()
        
        # Check 7: Force uWSGI reload using touch method
        print("[7] Attempting to force uWSGI reload...")
        wsgi_files = [
            "/var/www/html/src/app.py",
            "/var/www/html/src/wsgi.py",
            "/var/www/html/wsgi.py",
        ]
        for wsgi_file in wsgi_files:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {wsgi_file} && (touch {wsgi_file} && echo 'TOUCHED {wsgi_file}') || echo 'NOT_FOUND {wsgi_file}'")
            result = stdout.read().decode().strip()
            print(f"  {result}")
        print()
        
        # Check 8: Check uWSGI master PID and reload
        print("[8] Checking uWSGI master PID...")
        stdin, stdout, stderr = ssh.exec_command("systemctl show uwsgi-vidgenerator -p MainPID --value")
        master_pid = stdout.read().decode().strip()
        if master_pid and master_pid.isdigit():
            print(f"  Master PID: {master_pid}")
            print(f"  Attempting reload signal...")
            stdin, stdout, stderr = ssh.exec_command(f"kill -HUP {master_pid} 2>&1")
            reload_result = stdout.read().decode()
            if not reload_result:
                print(f"  [OK] Reload signal sent")
            else:
                print(f"  [WARN] {reload_result}")
        else:
            print(f"  [WARN] Could not get master PID")
        print()
        
        print("=" * 80)
        print("DIAGNOSIS COMPLETE")
        print("=" * 80)
        print()
        print("Recommendations:")
        print("1. If multiple uWSGI processes found, kill all and restart")
        print("2. If multiple battle.py files found, ensure correct one is being used")
        print("3. Try full service restart: sudo systemctl restart uwsgi-vidgenerator")
        print("4. Check uWSGI logs: journalctl -u uwsgi-vidgenerator -f")
        print()
        
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose()

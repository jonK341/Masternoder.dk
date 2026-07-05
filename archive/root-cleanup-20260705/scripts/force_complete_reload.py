#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Force Complete Reload - Kill all processes, clear cache, restart fresh
"""
import paramiko
import os
import time
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def force_complete_reload():
    """Force complete reload of all services"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        print("=" * 80)
        print("FORCING COMPLETE RELOAD")
        print("=" * 80)
        print()
        
        # Step 1: Stop all services
        print("[STEP 1] Stopping all services...")
        services = ['uwsgi', 'uwsgi-vidgenerator', 'python-proxy']
        for service in services:
            print(f"  Stopping {service}...")
            stdin, stdout, stderr = ssh.exec_command(f"sudo systemctl stop {service} 2>&1")
            stdout.read()
            stderr.read()
        time.sleep(3)
        print("  [OK] All services stopped")
        print()
        
        # Step 2: Kill any remaining processes
        print("[STEP 2] Killing any remaining processes...")
        kill_commands = [
            "sudo pkill -9 uwsgi 2>/dev/null || true",
            "sudo pkill -9 python-proxy 2>/dev/null || true",
            "sudo pkill -f 'python.*app.py' 2>/dev/null || true",
        ]
        for cmd in kill_commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.read()
            stderr.read()
        time.sleep(2)
        print("  [OK] All processes killed")
        print()
        
        # Step 3: Clear ALL Python cache
        print("[STEP 3] Clearing ALL Python cache...")
        cache_commands = [
            "find /var/www/html -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
            "find /var/www/html -type f -name '*.pyc' -delete 2>/dev/null || true",
            "find /var/www/html -type f -name '*.pyo' -delete 2>/dev/null || true",
            "rm -rf /tmp/*.pyc 2>/dev/null || true",
            "sync",
        ]
        for cmd in cache_commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.read()
            stderr.read()
        print("  [OK] All cache cleared")
        print()
        
        # Step 4: Touch WSGI file to force reload
        print("[STEP 4] Touching WSGI files to force reload...")
        wsgi_files = [
            "/var/www/html/src/app.py",
            "/var/www/html/src/wsgi.py",
            "/var/www/html/wsgi.py",
        ]
        for wsgi_file in wsgi_files:
            stdin, stdout, stderr = ssh.exec_command(f"touch {wsgi_file} 2>&1 || echo 'NOT_FOUND'")
            result = stdout.read().decode().strip()
            if 'NOT_FOUND' not in result:
                print(f"  [OK] Touched {wsgi_file}")
        print()
        
        # Step 5: Start services
        print("[STEP 5] Starting services...")
        for service in services:
            print(f"  Starting {service}...")
            stdin, stdout, stderr = ssh.exec_command(f"sudo systemctl start {service} 2>&1")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                print(f"  [OK] {service} started")
            else:
                error = stderr.read().decode()
                print(f"  [WARN] {service}: {error[:100]}")
        print()
        
        # Step 6: Wait for services to initialize
        print("[STEP 6] Waiting for services to initialize...")
        time.sleep(10)
        print("  [OK] Wait complete")
        print()
        
        # Step 7: Verify services are running
        print("[STEP 7] Verifying services...")
        for service in services:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service} 2>&1")
            status = stdout.read().decode().strip()
            if status == "active":
                print(f"  [OK] {service} is ACTIVE")
            else:
                print(f"  [FAIL] {service} status: {status}")
        print()
        
        print("=" * 80)
        print("RELOAD COMPLETE")
        print("=" * 80)
        print()
        print("Wait 15 seconds, then test endpoints:")
        print("  python test_all_battle_tabs.py")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = force_complete_reload()
    sys.exit(0 if success else 1)

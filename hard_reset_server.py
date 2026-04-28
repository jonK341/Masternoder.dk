#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hard Reset Server Script
Force complete restart of all services with cache clearing
"""
import paramiko
import os
import sys
import time

# Server configuration
SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_PATH = '/var/www/html/vidgenerator'

def execute_command(ssh, command, description):
    """Execute a command and return output"""
    try:
        print(f"[EXEC] {description}...")
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        errors = stderr.read().decode('utf-8', errors='ignore')
        
        if exit_status == 0:
            print(f"[OK] {description} completed")
            if output.strip():
                print(f"  Output: {output.strip()[:200]}")
        else:
            print(f"[WARN] {description} completed with exit code {exit_status}")
            if errors.strip():
                print(f"  Errors: {errors.strip()[:200]}")
        
        return exit_status == 0, output, errors
    except Exception as e:
        print(f"[ERROR] Failed to {description}: {e}")
        return False, "", str(e)

def main():
    print("="*80)
    print("HARD RESET SERVER - COMPLETE RESTART")
    print("="*80)
    print("This will:")
    print("  1. Stop all services (uWSGI, Python Proxy, Nginx)")
    print("  2. Clear all caches (Python, Nginx, system)")
    print("  3. Kill any hanging processes")
    print("  4. Restart all services")
    print("  5. Verify services are running")
    print("="*80)
    
    try:
        # Connect to server
        print("\n[1/6] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        
        # Step 1: Stop all services
        print("\n[2/6] Stopping all services...")
        stop_commands = [
            'systemctl stop python-proxy.service',
            'systemctl stop nginx',
            # Stop both legacy uwsgi init script and the real app service
            'systemctl stop uwsgi 2>/dev/null || true',
            'systemctl stop uwsgi-vidgenerator.service 2>/dev/null || true',
        ]
        for cmd in stop_commands:
            execute_command(ssh, cmd, f"Stopping {cmd.split()[-1]}")
        
        # Wait a moment for services to stop
        time.sleep(3)
        
        # Step 2: Kill any hanging processes
        print("\n[3/6] Killing hanging processes...")
        kill_commands = [
            'pkill -9 -f uwsgi || true',
            'pkill -9 -f python-proxy || true',
            'pkill -9 -f "python.*app.py" || true',
            'fuser -k 5000/tcp 2>/dev/null || true',  # Kill anything on port 5000
            'fuser -k 8080/tcp 2>/dev/null || true',  # Kill proxy port if stuck
        ]
        for cmd in kill_commands:
            execute_command(ssh, cmd, "Killing processes")
        
        time.sleep(2)
        
        # Step 3: Clear all caches
        print("\n[4/6] Clearing all caches...")
        cache_commands = [
            # Python cache
            'find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true',
            'find /var/www/html/vidgenerator -type f -name "*.pyc" -delete 2>/dev/null || true',
            'find /var/www/html/vidgenerator -type f -name "*.pyo" -delete 2>/dev/null || true',
            
            # Nginx cache
            'rm -rf /var/cache/nginx/* 2>/dev/null || true',
            'rm -rf /var/lib/nginx/cache/* 2>/dev/null || true',
            
            # System cache
            'sync',  # Flush filesystem buffers
            
            # uWSGI cache/sockets
            'rm -f /tmp/uwsgi*.sock 2>/dev/null || true',
            'rm -f /var/run/uwsgi/*.sock 2>/dev/null || true',
        ]
        for cmd in cache_commands:
            execute_command(ssh, cmd, "Clearing cache")
        
        # Step 4: Verify service files exist
        print("\n[5/6] Verifying service configurations...")
        verify_commands = [
            'systemctl daemon-reload',
            'systemctl status uwsgi --no-pager | head -3 || true',
            'systemctl status python-proxy.service --no-pager | head -3 || true',
            'systemctl status nginx --no-pager | head -3 || true',
        ]
        for cmd in verify_commands:
            execute_command(ssh, cmd, "Verifying services")
        
        # Step 5: Restart all services
        print("\n[6/6] Restarting all services...")
        restart_commands = [
            'systemctl start uwsgi-vidgenerator.service',
            'sleep 3',
            'systemctl start uwsgi 2>/dev/null || true',
            'sleep 1',
            'systemctl start python-proxy.service',
            'sleep 2',
            'systemctl start nginx',
            'sleep 2',
        ]
        for cmd in restart_commands:
            if cmd.startswith('sleep'):
                time.sleep(int(cmd.split()[1]))
            else:
                success, output, errors = execute_command(ssh, cmd, f"Starting {cmd.split()[-1]}")
                if not success and 'uwsgi' in cmd:
                    print("[WARN] uWSGI may need additional time to start")
        
        # Step 6: Verify services are running
        print("\n[VERIFY] Verifying services are running...")
        verify_services = [
            ('uwsgi-vidgenerator', 'systemctl is-active uwsgi-vidgenerator.service'),
            ('uwsgi', 'systemctl is-active uwsgi'),
            ('python-proxy', 'systemctl is-active python-proxy.service'),
            ('nginx', 'systemctl is-active nginx'),
        ]
        
        all_running = True
        for service_name, check_cmd in verify_services:
            success, output, errors = execute_command(ssh, check_cmd, f"Checking {service_name}")
            if 'active' in output.lower():
                print(f"[OK] {service_name} is running")
            else:
                print(f"[WARN] {service_name} status: {output.strip()}")
                all_running = False
        
        # Additional verification: Check if ports are listening
        print("\n[VERIFY] Checking if ports are listening...")
        port_checks = [
            ('5000', 'netstat -tlnp | grep :5000 || ss -tlnp | grep :5000 || true'),
            ('80', 'netstat -tlnp | grep :80 || ss -tlnp | grep :80 || true'),
        ]
        for port, check_cmd in port_checks:
            success, output, errors = execute_command(ssh, check_cmd, f"Checking port {port}")
            if output.strip():
                print(f"[OK] Port {port} is listening")
            else:
                print(f"[WARN] Port {port} may not be listening yet")
        
        ssh.close()
        
        print("\n" + "="*80)
        print("HARD RESET COMPLETE")
        print("="*80)
        if all_running:
            print("[SUCCESS] All services appear to be running")
        else:
            print("[WARNING] Some services may need additional time to start")
        print("\nPlease wait 15-30 seconds for services to fully initialize,")
        print("then run comprehensive_site_audit.py to verify all routes.")
        print("\nIf issues persist, check service logs:")
        print("  - sudo journalctl -u uwsgi -n 50")
        print("  - sudo journalctl -u python-proxy.service -n 50")
        print("  - sudo journalctl -u nginx -n 50")
        
    except paramiko.AuthenticationException:
        print("[ERROR] Authentication failed. Check DEPLOY_PASS environment variable.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Hard reset failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hard Restart All Services - Ensure all changes are active
"""
import paramiko
import os
import sys
import time

SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def main():
    print("="*80)
    print("HARD RESTART ALL SERVICES")
    print("="*80)
    
    try:
        print("\n[1/6] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        
        print("\n[2/6] Stopping services...")
        stop_commands = [
            'systemctl stop uwsgi-vidgenerator.service 2>/dev/null || true',
            'systemctl stop python-proxy.service 2>/dev/null || true',
            'sleep 2',
        ]
        for cmd in stop_commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("[OK] Services stopped")
        
        print("\n[3/6] Clearing all caches...")
        cache_commands = [
            'find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true',
            'find /var/www/html/vidgenerator -type f -name "*.pyc" -delete 2>/dev/null || true',
            'find /var/www/html/vidgenerator -type f -name "*.pyo" -delete 2>/dev/null || true',
            'rm -rf /tmp/uwsgi_* 2>/dev/null || true',
            'sync',
        ]
        for cmd in cache_commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("[OK] Cache cleared")
        
        print("\n[4/6] Starting uWSGI service...")
        stdin, stdout, stderr = ssh.exec_command('systemctl start uwsgi-vidgenerator.service')
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("[OK] uWSGI started")
            time.sleep(3)
        else:
            print(f"[WARNING] uWSGI start returned exit code {exit_status}")
        
        print("\n[5/6] Starting Python Proxy service...")
        stdin, stdout, stderr = ssh.exec_command('systemctl start python-proxy.service')
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("[OK] Python Proxy started")
            time.sleep(2)
        else:
            print(f"[WARNING] Python Proxy start returned exit code {exit_status}")
        
        print("\n[6/6] Restarting Nginx...")
        stdin, stdout, stderr = ssh.exec_command('systemctl restart nginx')
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("[OK] Nginx restarted")
        else:
            print(f"[WARNING] Nginx restart returned exit code {exit_status}")
        
        print("\n[CHECK] Verifying service status...")
        check_commands = [
            ('uwsgi-vidgenerator.service', 'systemctl is-active uwsgi-vidgenerator.service'),
            ('python-proxy.service', 'systemctl is-active python-proxy.service'),
            ('nginx', 'systemctl is-active nginx'),
        ]
        
        all_active = True
        for service_name, cmd in check_commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            status = stdout.read().decode('utf-8').strip()
            if status == 'active':
                print(f"  [OK] {service_name}: active")
            else:
                print(f"  [ERROR] {service_name}: {status}")
                all_active = False
        
        ssh.close()
        
        print("\n" + "="*80)
        print("RESTART COMPLETE")
        print("="*80)
        if all_active:
            print("[SUCCESS] All services restarted and active!")
            print("\nAll changes should now be active:")
            print("  - Click game enhancements (story, energy, triggers, effects)")
            print("  - Grid loading fixes")
            print("  - Comprehensive points display")
            print("  - Stats refresh endpoint fix")
        else:
            print("[WARNING] Some services may not be active - check status above")
        
    except paramiko.AuthenticationException:
        print("[ERROR] Authentication failed. Check DEPLOY_PASS environment variable.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Restart failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

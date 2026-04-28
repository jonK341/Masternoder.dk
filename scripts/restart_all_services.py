#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Restart All Services - Complete service restart
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def restart_all():
    """Restart all services"""
    ssh = None
    try:
        print("=" * 70)
        print("RESTARTING ALL SERVICES")
        print("=" * 70)
        print()
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        services = [
            ('python-proxy.service', 'python-proxy'),
            ('uwsgi-vidgenerator', 'uwsgi'),
            ('nginx', 'nginx'),
            ('apache2', 'apache2')
        ]
        
        for service_name, display_name in services:
            print(f"Restarting {display_name}...")
            try:
                # Stop
                ssh.exec_command(f"systemctl stop {service_name} 2>&1 || true", timeout=10)
                time.sleep(2)
                
                # Start
                stdin, stdout, stderr = ssh.exec_command(f"systemctl start {service_name} 2>&1", timeout=30)
                output = stdout.read().decode('utf-8', errors='ignore')
                error = stderr.read().decode('utf-8', errors='ignore')
                
                # Check status
                time.sleep(3)
                stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service_name} 2>&1", timeout=5)
                status = stdout.read().decode('utf-8', errors='ignore').strip()
                
                if status == 'active':
                    print(f"  [OK] {display_name} is active")
                else:
                    print(f"  [WARN] {display_name} status: {status}")
            except Exception as e:
                print(f"  [ERROR] {display_name}: {e}")
            print()
        
        # Final status check
        print("Final service status:")
        for service_name, display_name in services:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service_name} 2>&1", timeout=5)
            status = stdout.read().decode('utf-8', errors='ignore').strip()
            print(f"  {display_name}: {status}")
        print()
        
        print("=" * 70)
        print("SERVICES RESTARTED")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh:
            ssh.close()

if __name__ == '__main__':
    restart_all()

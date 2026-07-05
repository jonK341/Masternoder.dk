#!/usr/bin/env python3
"""
Service Restart Buffer System
Provides safe service restart with buffers and coupling checks
"""
import paramiko
import time
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

class ServiceRestartBuffer:
    """Service restart with buffer and coupling"""
    
    def __init__(self):
        self.ssh = None
        self.connect()
    
    def connect(self):
        """Connect to server"""
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    
    def check_service_status(self, service_name):
        """Check service status"""
        stdin, stdout, stderr = self.ssh.exec_command(f"systemctl is-active {service_name}")
        status = stdout.read().decode('utf-8').strip()
        return status == 'active'
    
    def wait_for_service(self, service_name, timeout=30):
        """Wait for service to become active"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.check_service_status(service_name):
                return True
            time.sleep(1)
        return False
    
    def stop_service(self, service_name, timeout=15):
        """Stop service safely"""
        print(f"  [STOP] {service_name}...")
        stdin, stdout, stderr = self.ssh.exec_command(f"systemctl stop {service_name}")
        stdout.read()
        time.sleep(2)  # Buffer after stop
        return True
    
    def start_service(self, service_name, timeout=15):
        """Start service safely"""
        print(f"  [START] {service_name}...")
        stdin, stdout, stderr = self.ssh.exec_command(f"systemctl start {service_name}")
        stdout.read()
        time.sleep(3)  # Buffer after start
        return True
    
    def restart_with_buffer(self):
        """Restart services with proper buffers"""
        print("=" * 80)
        print("SERVICE RESTART WITH BUFFER")
        print("=" * 80)
        print()
        
        # Step 1: Check current status
        print("[STEP 1] Checking current service status...")
        uwsgi_active = self.check_service_status('uwsgi-vidgenerator.service')
        apache_active = self.check_service_status('apache2.service')
        print(f"  uWSGI: {'active' if uwsgi_active else 'inactive'}")
        print(f"  Apache: {'active' if apache_active else 'inactive'}")
        print()
        
        # Step 2: Stop services with buffer
        print("[STEP 2] Stopping services (with buffer)...")
        if uwsgi_active:
            self.stop_service('uwsgi-vidgenerator.service')
        if apache_active:
            self.stop_service('apache2.service')
        
        # Buffer wait
        print("  [BUFFER] Waiting 5 seconds...")
        time.sleep(5)
        print()
        
        # Step 3: Verify stopped
        print("[STEP 3] Verifying services stopped...")
        uwsgi_stopped = not self.check_service_status('uwsgi-vidgenerator.service')
        apache_stopped = not self.check_service_status('apache2.service')
        print(f"  uWSGI stopped: {uwsgi_stopped}")
        print(f"  Apache stopped: {apache_stopped}")
        print()
        
        # Step 4: Start services with buffer
        print("[STEP 4] Starting services (with buffer)...")
        self.start_service('uwsgi-vidgenerator.service')
        self.start_service('apache2.service')
        
        # Buffer wait
        print("  [BUFFER] Waiting 5 seconds...")
        time.sleep(5)
        print()
        
        # Step 5: Verify started
        print("[STEP 5] Verifying services started...")
        uwsgi_started = self.wait_for_service('uwsgi-vidgenerator.service', timeout=30)
        apache_started = self.wait_for_service('apache2.service', timeout=30)
        
        print(f"  uWSGI started: {uwsgi_started}")
        print(f"  Apache started: {apache_started}")
        print()
        
        # Step 6: Final status check
        print("[STEP 6] Final status check...")
        uwsgi_final = self.check_service_status('uwsgi-vidgenerator.service')
        apache_final = self.check_service_status('apache2.service')
        
        print(f"  uWSGI: {'✅ ACTIVE' if uwsgi_final else '❌ INACTIVE'}")
        print(f"  Apache: {'✅ ACTIVE' if apache_final else '❌ INACTIVE'}")
        print()
        
        # Step 7: Check for errors
        print("[STEP 7] Checking for errors...")
        stdin, stdout, stderr = self.ssh.exec_command(
            "tail -n 20 /var/log/uwsgi/vidgenerator.log | grep -i error || echo 'No recent errors'"
        )
        errors = stdout.read().decode('utf-8')
        if 'No recent errors' not in errors:
            print(f"  ⚠️  Recent errors found:")
            print(f"  {errors}")
        else:
            print("  ✅ No recent errors")
        print()
        
        return uwsgi_final and apache_final
    
    def check_coupling(self):
        """Check service coupling (dependencies)"""
        print("[COUPLING] Checking service dependencies...")
        
        # Check if uWSGI socket exists
        stdin, stdout, stderr = self.ssh.exec_command(
            "test -S /var/www/html/vidgenerator/vidgenerator.sock && echo 'exists' || echo 'missing'"
        )
        socket_status = stdout.read().decode('utf-8').strip()
        print(f"  uWSGI socket: {socket_status}")
        
        # Check Apache proxy configuration
        stdin, stdout, stderr = self.ssh.exec_command(
            "grep -i 'ProxyPass.*vidgenerator' /etc/apache2/sites-enabled/*.conf | head -1 || echo 'not found'"
        )
        proxy_config = stdout.read().decode('utf-8').strip()
        if 'not found' not in proxy_config:
            print(f"  ✅ Apache proxy configured")
        else:
            print(f"  ⚠️  Apache proxy config not found")
        
        return socket_status == 'exists'
    
    def close(self):
        """Close SSH connection"""
        if self.ssh:
            self.ssh.close()

def main():
    buffer = ServiceRestartBuffer()
    
    try:
        # Check coupling first
        coupling_ok = buffer.check_coupling()
        print()
        
        if not coupling_ok:
            print("⚠️  Coupling issues detected, but proceeding with restart...")
            print()
        
        # Restart with buffer
        success = buffer.restart_with_buffer()
        
        print("=" * 80)
        if success:
            print("✅ SERVICES RESTARTED SUCCESSFULLY")
        else:
            print("❌ SERVICES RESTART FAILED")
        print("=" * 80)
        
    finally:
        buffer.close()

if __name__ == '__main__':
    main()


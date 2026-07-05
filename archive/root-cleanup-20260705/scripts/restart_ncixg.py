#!/usr/bin/env python3
"""
Restart Ncixg Service
Python script to stop/start/restart the service
Usage: python restart_ncixg.py [off|on|restart]
"""
import sys
import os
import subprocess
import time

def run_command(cmd, description):
    """Run a command and return success status"""
    try:
        print(f"  {description}...")
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"  ✅ {description} completed")
            return True
        else:
            print(f"  ⚠️  {description} returned code {result.returncode}")
            if result.stderr:
                print(f"     Error: {result.stderr[:100]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ⏱️  {description} timed out")
        return False
    except Exception as e:
        print(f"  ❌ {description} failed: {e}")
        return False

def stop_service():
    """Stop the service"""
    print("=" * 50)
    print("STOPPING NCIXG SERVICE")
    print("=" * 50)
    print()
    
    services = [
        ("nginx", "Stopping nginx"),
        ("uwsgi-vidgenerator.service", "Stopping uwsgi-vidgenerator"),
        ("python-proxy.service", "Stopping python-proxy")
    ]
    
    for service, desc in services:
        # Try systemctl first (Linux)
        run_command(f"sudo systemctl stop {service} 2>/dev/null", desc)
        # Fallback to service command
        if service.endswith('.service'):
            service_name = service.replace('.service', '')
        else:
            service_name = service
        run_command(f"sudo service {service_name} stop 2>/dev/null", f"{desc} (service)")
    
    print()
    print("=" * 50)
    print("SERVICE STOPPED")
    print("=" * 50)
    return True

def start_service():
    """Start the service"""
    print("=" * 50)
    print("STARTING NCIXG SERVICE")
    print("=" * 50)
    print()
    
    # Start in order
    services = [
        ("python-proxy.service", "Starting python-proxy"),
        ("uwsgi-vidgenerator.service", "Starting uwsgi-vidgenerator"),
        ("nginx", "Starting nginx")
    ]
    
    for service, desc in services:
        # Try systemctl first (Linux)
        success = run_command(f"sudo systemctl start {service} 2>/dev/null", desc)
        # Fallback to service command
        if not success:
            if service.endswith('.service'):
                service_name = service.replace('.service', '')
            else:
                service_name = service
            run_command(f"sudo service {service_name} start 2>/dev/null", f"{desc} (service)")
        
        # Wait between services
        if service != services[-1][0]:
            time.sleep(2)
    
    # Wait for services to stabilize
    print()
    print("Waiting for services to stabilize...")
    time.sleep(3)
    
    # Verify services
    print()
    print("Verifying service status...")
    print("-" * 50)
    
    for service, _ in services:
        if service.endswith('.service'):
            service_name = service.replace('.service', '')
        else:
            service_name = service
        
        # Check status
        result = subprocess.run(
            f"sudo systemctl is-active {service} 2>/dev/null",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and 'active' in result.stdout:
            print(f"  ✅ {service_name}: active")
        else:
            print(f"  ⚠️  {service_name}: inactive")
    
    print()
    print("=" * 50)
    print("SERVICE STARTED")
    print("=" * 50)
    return True

def restart_service():
    """Restart the service"""
    print("=" * 50)
    print("RESTARTING NCIXG SERVICE")
    print("=" * 50)
    print()
    
    stop_service()
    print()
    time.sleep(2)
    start_service()
    
    return True

def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
    else:
        command = 'restart'
    
    if command == 'off' or command == 'stop':
        stop_service()
    elif command == 'on' or command == 'start':
        start_service()
    elif command == 'restart':
        restart_service()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python restart_ncixg.py [off|on|restart]")
        sys.exit(1)

if __name__ == '__main__':
    main()

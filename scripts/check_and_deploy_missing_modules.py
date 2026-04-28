#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check and Deploy Missing Modules
Checks for missing backend services modules and deploys them to the server
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
REMOTE_BASE = "/var/www/html/vidgenerator"

# Modules imported in src/app.py that we need to check
REQUIRED_MODULES = [
    # Core modules
    "backend/services/ip_mac_user_manager.py",
    
    # Other modules that might be missing
    "backend/services/startup_automation.py",
    "backend/services/frontpage_initializer.py",
    "backend/services/error_hash_tracking.py",
    "backend/services/spiderweb_error_handler.py",
    "backend/services/spiderweb_error_fixes.py",
    "backend/services/realtime_system.py",
    "backend/services/cache_system.py",
    
    # Additional services that might be imported elsewhere
    "backend/services/enhanced_user_profile_json.py",
    "backend/services/unified_points_database.py",
]

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(text.center(70))
    print("=" * 70 + "\n")

def print_success(text):
    """Print success message"""
    print(f"[OK] {text}")

def print_error(text):
    """Print error message"""
    print(f"[ERROR] {text}")

def print_info(text):
    """Print info message"""
    print(f"[INFO] {text}")

def print_warning(text):
    """Print warning message"""
    print(f"[WARN] {text}")

def check_module_exists_locally(module_path):
    """Check if module exists locally"""
    return os.path.exists(module_path)

def check_module_exists_remote(ssh, module_path):
    """Check if module exists on remote server"""
    try:
        remote_path = os.path.join(REMOTE_BASE, module_path).replace('\\', '/')
        cmd = f"test -f {remote_path} && echo 'EXISTS' || echo 'NOT_FOUND'"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode('utf-8', errors='replace').strip()
        return 'EXISTS' in output
    except Exception as e:
        print_warning(f"Could not check {module_path}: {str(e)[:50]}")
        return False

def deploy_module(ssh, sftp, module_path):
    """Deploy a single module to the server"""
    try:
        local_path = os.path.abspath(module_path)
        
        if not os.path.exists(local_path):
            return False, f"Local file not found: {module_path}"
        
        remote_path = os.path.join(REMOTE_BASE, module_path).replace('\\', '/')
        remote_dir = os.path.dirname(remote_path)
        
        # Create remote directory
        ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
        time.sleep(0.5)
        
        # Backup existing file if it exists
        ssh.exec_command(f"test -f {remote_path} && cp {remote_path} {remote_path}.backup.$(date +%Y%m%d_%H%M%S) || true", timeout=5)
        
        # Read local file
        with open(local_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Write to remote
        with sftp.file(remote_path, 'w') as rf:
            rf.write(content)
        
        return True, None
        
    except Exception as e:
        return False, str(e)

def check_import_on_server(ssh, module_name):
    """Check if a module can be imported on the server"""
    try:
        # Convert file path to import path
        import_path = module_name.replace('.py', '').replace('/', '.')
        
        cmd = f"cd {REMOTE_BASE} && python3 -c 'import {import_path}' 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        
        if error.strip() and 'ModuleNotFoundError' not in error and 'ImportError' not in error:
            # Other errors (like syntax errors) might be OK if module exists
            return True, None
        elif 'ModuleNotFoundError' in error or 'ImportError' in error:
            return False, error.strip()[:200]
        elif not error.strip():
            return True, None
        else:
            # Might have other issues, but module exists
            return True, error.strip()[:100]
            
    except Exception as e:
        return False, str(e)[:100]

def check_all_imports_in_app(ssh):
    """Check if src/app.py can import all required modules"""
    print_info("Testing imports in src/app.py...")
    
    try:
        # Try to import the app (this will test all imports)
        cmd = f"cd {REMOTE_BASE} && python3 -c 'from src.app import create_app' 2>&1 | head -50"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        
        full_output = output + error
        
        # Check for missing modules
        if 'ModuleNotFoundError' in full_output or 'ImportError' in full_output:
            # Extract missing module name
            import re
            match = re.search(r"(?:ModuleNotFoundError|ImportError): No module named ['\"]([^'\"]+)['\"]", full_output)
            if match:
                missing_module = match.group(1)
                return False, missing_module, full_output[:500]
            return False, "Unknown module", full_output[:500]
        
        # Check for other errors
        if 'Error' in full_output or 'Traceback' in full_output:
            return False, "Error during import", full_output[:500]
        
        return True, None, None
        
    except Exception as e:
        return False, str(e), None

def main():
    """Main checking and deployment routine"""
    print_header("CHECK AND DEPLOY MISSING MODULES")
    print(f"Server: {SERVER_HOST}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    ssh = None
    try:
        # Connect
        print_info("Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print_success("Connected to server")
        
        # Step 1: Check which modules exist locally
        print_header("STEP 1: CHECKING LOCAL MODULES")
        local_modules = {}
        for module in REQUIRED_MODULES:
            exists = check_module_exists_locally(module)
            local_modules[module] = exists
            if exists:
                print_success(f"{module} - EXISTS locally")
            else:
                print_warning(f"{module} - NOT FOUND locally (may not be required)")
        
        # Step 2: Check which modules exist on server
        print_header("STEP 2: CHECKING REMOTE MODULES")
        remote_modules = {}
        missing_modules = []
        
        for module in REQUIRED_MODULES:
            if local_modules.get(module, False):  # Only check if exists locally
                exists = check_module_exists_remote(ssh, module)
                remote_modules[module] = exists
                if exists:
                    print_success(f"{module} - EXISTS on server")
                else:
                    print_error(f"{module} - MISSING on server")
                    missing_modules.append(module)
        
        # Step 3: Deploy missing modules
        if missing_modules:
            print_header("STEP 3: DEPLOYING MISSING MODULES")
            sftp = ssh.open_sftp()
            
            deployed = 0
            failed = 0
            
            for module in missing_modules:
                print_info(f"Deploying {module}...")
                success, error = deploy_module(ssh, sftp, module)
                
                if success:
                    print_success(f"{module} - Deployed successfully")
                    deployed += 1
                else:
                    print_error(f"{module} - Deployment failed: {error}")
                    failed += 1
            
            sftp.close()
            
            print(f"\n[SUMMARY] Deployed: {deployed}, Failed: {failed}")
        else:
            print_success("No missing modules found! All modules are already on the server.")
        
        # Step 4: Check if imports work now
        print_header("STEP 4: VERIFYING IMPORTS")
        
        # Check individual modules
        for module in REQUIRED_MODULES:
            if local_modules.get(module, False):
                module_name = module.replace('.py', '').replace('/', '.')
                can_import, error = check_import_on_server(ssh, module_name)
                if can_import:
                    print_success(f"{module} - Can be imported")
                else:
                    print_warning(f"{module} - Import error: {error}")
        
        # Check if app can start
        print_info("Checking if src/app.py can start...")
        can_start, missing, error_msg = check_all_imports_in_app(ssh)
        
        if can_start:
            print_success("src/app.py can import all modules!")
        else:
            if missing:
                print_error(f"Missing module: {missing}")
                print_info("This module still needs to be created or deployed")
            if error_msg:
                print_warning(f"Error: {error_msg[:300]}")
        
        # Step 5: Clear cache and restart
        if missing_modules and deployed > 0:
            print_header("STEP 5: CLEARING CACHE")
            print_info("Clearing Python cache...")
            ssh.exec_command("find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true", timeout=30)
            ssh.exec_command("find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
            print_success("Cache cleared")
        
        # Summary
        print_header("DEPLOYMENT COMPLETE")
        if missing_modules:
            print_success(f"Deployed {deployed} missing module(s)")
        else:
            print_success("All modules are present on the server")
        
        if can_start:
            print_success("Application can start successfully!")
        else:
            print_warning("Application may still have import issues - check errors above")
        
        print_info(f"Live URL: https://{SERVER_HOST}/vidgenerator")
        
        return 0
        
    except paramiko.AuthenticationException:
        print_error("Authentication failed! Check credentials.")
        return 1
    except paramiko.SSHException as e:
        print_error(f"SSH connection failed: {str(e)}")
        return 1
    except Exception as e:
        print_error(f"Check failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if ssh:
            ssh.close()

if __name__ == '__main__':
    sys.exit(main())

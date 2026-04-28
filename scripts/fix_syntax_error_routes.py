#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Syntax Error in Server Routes File
Fixes the syntax error in /var/www/html/vidgenerator/src/web/routes/__init__.py
"""
import paramiko
import os
import sys
import time
import re
from datetime import datetime

# Fix Windows encoding issues
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_FILE = "/var/www/html/vidgenerator/src/web/routes/__init__.py"

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

def read_file_section(ssh, file_path, start_line, end_line):
    """Read a section of a file from the server"""
    try:
        cmd = f"sed -n '{start_line},{end_line}p' {file_path} 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        
        if error.strip() and 'No such file' in error:
            return None, f"File not found: {error}"
        return output, None
    except Exception as e:
        return None, str(e)

def check_syntax_error(ssh, file_path):
    """Check for syntax errors in the file"""
    print_info("Checking for syntax errors...")
    try:
        cmd = f"python3 -m py_compile {file_path} 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        
        if error.strip():
            # Parse error message for line number
            line_match = re.search(r'line (\d+)', error)
            if line_match:
                line_num = int(line_match.group(1))
                print_error(f"Syntax error found at line {line_num}")
                print_info(f"Error: {error.strip()[:200]}")
                return line_num, error
            else:
                print_error(f"Syntax error: {error.strip()[:200]}")
                return None, error
        
        if "SyntaxError" in output or "IndentationError" in output:
            line_match = re.search(r'line (\d+)', output)
            if line_match:
                line_num = int(line_match.group(1))
                print_error(f"Syntax error found at line {line_num}")
                return line_num, output
            return None, output
        
        print_success("No syntax errors found!")
        return None, None
        
    except Exception as e:
        print_error(f"Could not check syntax: {str(e)}")
        return None, str(e)

def fix_except_block(ssh, file_path, error_line):
    """Fix the except block syntax error"""
    print_info(f"Reading file section around line {error_line}...")
    
    # Read context around the error line (15 lines before, 15 lines after)
    start_line = max(1, error_line - 15)
    end_line = error_line + 15
    
    content, error = read_file_section(ssh, file_path, start_line, end_line)
    if content is None:
        print_error(f"Could not read file section: {error}")
        return False
    
    lines = content.split('\n')
    print_info("File section read. Analyzing...")
    
    # Display the problematic section
    print("\n" + "-" * 70)
    print("PROBLEMATIC SECTION:")
    print("-" * 70)
    for i, line in enumerate(lines, start=start_line):
        marker = " >>> " if i == error_line else "     "
        print(f"{marker}{i:4d}: {line}")
    print("-" * 70 + "\n")
    
    # Read the entire file to fix it
    print_info("Reading entire file for fixing...")
    try:
        cmd = f"cat {file_path} 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
        full_content = stdout.read().decode('utf-8', errors='replace')
        error_output = stderr.read().decode('utf-8', errors='replace')
        
        if error_output.strip() and 'No such file' in error_output:
            print_error(f"File not found: {error_output}")
            return False
        
        if not full_content.strip():
            print_error("File is empty or could not be read")
            return False
        
        file_lines = full_content.split('\n')
        fixed_lines = []
        fixed = False
        
        # Find and fix the problematic except block around error_line
        for i in range(len(file_lines)):
            line = file_lines[i]
            line_num = i + 1
            
            # Check if we're near the error line and this is an except statement
            if abs(line_num - error_line) <= 5:
                if re.match(r'^\s*except\s', line) or re.match(r'^\s*except\s+Exception', line) or re.match(r'^\s*except\s+ImportError', line):
                    # Get indentation of except line
                    except_indent = len(line) - len(line.lstrip())
                    
                    # Check next few lines to see if block is empty
                    next_non_empty = None
                    for j in range(i + 1, min(i + 10, len(file_lines))):
                        if file_lines[j].strip():
                            next_non_empty = j
                            next_line = file_lines[j]
                            next_indent = len(next_line) - len(next_line.lstrip())
                            break
                    
                    # If no next line or next line has same/less indentation, except block is empty
                    if next_non_empty is None or (next_indent <= except_indent):
                        # Check if pass already exists in the except block
                        has_pass = False
                        for j in range(i + 1, min(i + 5, len(file_lines))):
                            check_line = file_lines[j]
                            check_indent = len(check_line) - len(check_line.lstrip())
                            if check_indent > except_indent and 'pass' in check_line:
                                has_pass = True
                                break
                        
                        if not has_pass:
                            print_info(f"Found empty except block at line {line_num}")
                            print_info(f"Adding 'pass' statement after line {line_num}")
                            
                            # Add the except line
                            fixed_lines.append(line)
                            
                            # Add pass statement with proper indentation (except_indent + 4 spaces)
                            pass_line = ' ' * (except_indent + 4) + 'pass'
                            fixed_lines.append(pass_line)
                            fixed = True
                            continue
            
            fixed_lines.append(line)
        
        if not fixed:
            # If we didn't find it with the above method, try a different approach
            # Look for any except block that might be empty near the error line
            print_warning("Could not automatically detect the exact issue. Trying alternative fix...")
            
            # Use sed to add pass after empty except blocks near the error line
            for i in range(max(0, error_line - 10), min(len(file_lines), error_line + 10)):
                line = file_lines[i]
                if re.match(r'^\s*except\s', line):
                    except_indent = len(line) - len(line.lstrip())
                    # Check if next line is problematic
                    if i + 1 < len(file_lines):
                        next_line = file_lines[i + 1]
                        next_indent = len(next_line) - len(next_line.lstrip()) if next_line.strip() else 0
                        
                        if not next_line.strip() or next_indent <= except_indent:
                            # Insert pass after this except
                            print_info(f"Fixing empty except block at line {i+1}")
                            file_lines.insert(i + 1, ' ' * (except_indent + 4) + 'pass')
                            fixed = True
                            break
            
            if fixed:
                fixed_lines = file_lines
                
    except Exception as e:
        print_error(f"Could not read/fix file: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    if not fixed:
        print_error("Could not automatically fix the syntax error")
        print_info("Manual editing may be required")
        return False
    
    # Backup original file
    print_info("Creating backup of original file...")
    try:
        backup_cmd = f"cp {file_path} {file_path}.backup.$(date +%Y%m%d_%H%M%S) 2>&1"
        stdin, stdout, stderr = ssh.exec_command(backup_cmd, timeout=10)
        stdout.read()
        print_success("Backup created")
    except Exception as e:
        print_warning(f"Could not create backup: {str(e)}")
    
    # Write fixed content back
    print_info("Writing fixed content...")
    try:
        sftp = ssh.open_sftp()
        with sftp.file(file_path, 'w') as f:
            f.write('\n'.join(fixed_lines))
        sftp.close()
        print_success("File updated")
        return True
    except Exception as e:
        print_error(f"Could not write file: {str(e)}")
        return False

def verify_fix(ssh, file_path):
    """Verify the syntax fix worked"""
    print_info("Verifying fix...")
    line_num, error = check_syntax_error(ssh, file_path)
    
    if line_num is None and error is None:
        print_success("Syntax error fixed!")
        return True
    else:
        print_error(f"Syntax error still exists at line {line_num}")
        print_info(f"Error: {error[:200]}")
        return False

def restart_services(ssh):
    """Restart Flask services"""
    print_header("RESTARTING SERVICES")
    
    services = ['python-proxy.service', 'vidgenerator-gunicorn.service', 'uwsgi-vidgenerator.service']
    
    try:
        # Stop services
        print_info("Stopping services...")
        for service in services:
            try:
                stdin, stdout, stderr = ssh.exec_command(f"systemctl stop {service} 2>&1", timeout=10)
                stdout.read()
                stderr.read()
            except:
                pass
        
        time.sleep(3)
        print_success("Services stopped")
        
        # Clear cache
        print_info("Clearing Python cache...")
        ssh.exec_command("find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        ssh.exec_command("find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print_success("Cache cleared")
        
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
                print_warning(f"{service}: {str(e)[:100]}")
        
        time.sleep(5)
        print_success("Services started")
        
        # Verify services
        print_info("Verifying services...")
        for service in services:
            try:
                stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service} 2>&1", timeout=5)
                status = stdout.read().decode('utf-8', errors='replace').strip()
                if 'active' in status.lower() or 'running' in status.lower():
                    print_success(f"{service}: Running")
                else:
                    print_info(f"{service}: {status}")
            except:
                pass
        
        return True
    except Exception as e:
        print_error(f"Service restart failed: {str(e)}")
        return False

def check_recent_errors(ssh):
    """Check recent error logs"""
    print_info("Checking recent error logs...")
    
    try:
        log_commands = [
            ("Python proxy log", "journalctl -u python-proxy.service -n 30 --no-pager 2>&1 | tail -20 || echo 'No log'"),
            ("Gunicorn log", "journalctl -u vidgenerator-gunicorn.service -n 30 --no-pager 2>&1 | tail -20 || echo 'No log'"),
            ("uWSGI log", "journalctl -u uwsgi-vidgenerator.service -n 30 --no-pager 2>&1 | tail -20 || echo 'No log'"),
            ("Recent Python errors", "find /var/www/html/vidgenerator -name '*.log' -type f -exec tail -10 {} \\; 2>&1 | head -30 || echo 'No log files'"),
        ]
        
        errors_found = False
        for name, cmd in log_commands:
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
                output = stdout.read().decode('utf-8', errors='replace')
                if output.strip() and 'No log' not in output[:20] and output.strip():
                    # Check for error keywords
                    if any(keyword in output.lower() for keyword in ['error', 'exception', 'traceback', 'failed', 'fail']):
                        print_warning(f"{name} contains errors:")
                        print(f"  {output[:500]}")
                        errors_found = True
            except:
                pass
        
        if not errors_found:
            print_success("No obvious errors found in recent logs")
    except Exception as e:
        print_info(f"Could not check logs: {str(e)[:100]}")

def test_endpoint():
    """Test if the endpoint is now working"""
    print_header("TESTING ENDPOINT")
    
    try:
        import importlib
        requests = importlib.import_module('requests')
        
        print_info("Testing live endpoint...")
        response = requests.get(f"https://{SERVER_HOST}/vidgenerator", timeout=10, verify=False)
        
        if response.status_code == 200:
            print_success(f"Server is responding! Status: {response.status_code}")
            print_info(f"Response size: {len(response.content)} bytes")
            return True
        elif response.status_code == 500:
            print_warning(f"Server error (500) - may need more time to start")
            return False
        elif response.status_code == 502:
            print_warning(f"Bad Gateway (502) - service may still be starting")
            return False
        else:
            print_info(f"Server responded with status: {response.status_code}")
            return response.status_code < 500
            
    except ImportError:
        print_info("requests module not available - skipping endpoint test")
        return None
    except Exception as e:
        print_info(f"Endpoint test: {str(e)[:100]} (may still be starting)")
        return None

def main():
    """Main fixing routine"""
    print_header("FIX SYNTAX ERROR IN ROUTES FILE")
    print(f"Server: {SERVER_HOST}")
    print(f"File: {REMOTE_FILE}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    ssh = None
    try:
        # Connect
        print_info("Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print_success("Connected to server")
        
        # Step 1: Check for syntax errors
        print_header("STEP 1: CHECKING FOR SYNTAX ERRORS")
        error_line, error_msg = check_syntax_error(ssh, REMOTE_FILE)
        
        if error_line is None:
            print_success("No syntax errors found! The file may have been fixed already.")
            print_info("Proceeding with service restart...")
        else:
            # Step 2: Fix the syntax error
            print_header("STEP 2: FIXING SYNTAX ERROR")
            if not fix_except_block(ssh, REMOTE_FILE, error_line):
                print_error("Could not fix the syntax error automatically")
                print_info("Manual intervention may be required")
                return 1
            
            # Step 3: Verify the fix
            print_header("STEP 3: VERIFYING FIX")
            if not verify_fix(ssh, REMOTE_FILE):
                print_error("Fix verification failed")
                print_info("The file may need manual editing")
                return 1
        
        # Step 4: Restart services
        if not restart_services(ssh):
            print_warning("Service restart had issues, but continuing...")
        
        # Step 5: Wait for services to start
        print_header("WAITING FOR SERVICES TO START")
        print_info("Waiting 10 seconds for services to fully start...")
        time.sleep(10)
        
        # Step 6: Check logs for any remaining errors
        print_header("CHECKING SERVER LOGS")
        check_recent_errors(ssh)
        
        # Step 7: Test endpoint
        test_result = test_endpoint()
        
        # Summary
        print_header("FIX COMPLETE")
        if test_result is True:
            print_success("Server is now responding correctly!")
        elif test_result is False:
            print_warning("Server may need more time to start, or there may be other issues")
            print_info("Check the logs above for specific error details")
        else:
            print_info("Could not verify endpoint (requests module not available)")
        
        print_info(f"Live URL: https://{SERVER_HOST}/vidgenerator")
        print_info("If issues persist, check server logs above")
        
        return 0
        
    except paramiko.AuthenticationException:
        print_error("Authentication failed! Check credentials.")
        return 1
    except paramiko.SSHException as e:
        print_error(f"SSH connection failed: {str(e)}")
        return 1
    except Exception as e:
        print_error(f"Fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if ssh:
            ssh.close()

if __name__ == '__main__':
    sys.exit(main())

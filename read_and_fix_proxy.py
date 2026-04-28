"""
Read Python proxy script and fix it properly
"""
import paramiko
import os
import sys
import time

# Configure UTF-8 for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv('DEPLOY_HOST', 'masternoder.dk')
USERNAME = os.getenv('DEPLOY_USER', 'root')
PASSWORD = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

print("=" * 80)
print("READING AND FIXING PYTHON PROXY SCRIPT")
print("=" * 80)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {SERVER_HOST}...")
    ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    print("[OK] Connected!")
    print()

    proxy_script = "/var/www/html/vidgenerator/python_proxy_server.py"
    
    # Restore from latest backup
    print("[1] Restoring from latest backup...")
    stdin, stdout, stderr = ssh.exec_command(f"ls -t {proxy_script}.backup.* 2>/dev/null | head -1")
    backup_file = stdout.read().decode('utf-8', errors='ignore').strip()
    if backup_file:
        stdin, stdout, stderr = ssh.exec_command(f"cp {backup_file} {proxy_script}")
        print(f"[OK] Restored from: {backup_file}")
    
    # Read the clean script
    print("[2] Reading proxy script...")
    stdin, stdout, stderr = ssh.exec_command(f"cat {proxy_script}")
    proxy_code = stdout.read().decode('utf-8', errors='ignore')
    
    print(f"Script length: {len(proxy_code)} characters")
    print("\nScript structure:")
    lines = proxy_code.split('\n')
    for i, line in enumerate(lines[:30], 1):
        print(f"{i:3}: {line}")
    print()
    
    # Create backup
    stdin, stdout, stderr = ssh.exec_command(f"cp {proxy_script} {proxy_script}.backup.$(date +%Y%m%d_%H%M%S)")
    print("[OK] Backup created")
    
    # Find where to insert static file handler (after class definition, before first method)
    class_line = None
    first_method_line = None
    for i, line in enumerate(lines):
        if 'class ProxyHandler' in line:
            class_line = i
        if class_line is not None and first_method_line is None and 'def ' in line and 'ProxyHandler' not in line:
            first_method_line = i
            break
    
    if class_line is not None and first_method_line is not None:
        print(f"[3] Found class at line {class_line+1}, first method at line {first_method_line+1}")
        
        # Get indentation from first method
        first_method = lines[first_method_line]
        indent = len(first_method) - len(first_method.lstrip())
        indent_str = ' ' * indent
        
        # Create static file handler with correct indentation
        static_handler = f'''{indent_str}def handle_static_file(self, path):
{indent_str}    """Handle static files directly without proxying"""
{indent_str}    import os
{indent_str}    static_base = '/var/www/html/vidgenerator/vidgenerator/static'
{indent_str}    static_path = path.replace('/vidgenerator/static/', '')
{indent_str}    file_path = os.path.join(static_base, static_path)
{indent_str}    
{indent_str}    if os.path.exists(file_path) and os.path.isfile(file_path):
{indent_str}        try:
{indent_str}            with open(file_path, 'rb') as f:
{indent_str}                content = f.read()
{indent_str}            
{indent_str}            # Determine content type
{indent_str}            content_type = 'text/css'
{indent_str}            if file_path.endswith('.js'):
{indent_str}                content_type = 'application/javascript'
{indent_str}            elif file_path.endswith('.png'):
{indent_str}                content_type = 'image/png'
{indent_str}            elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
{indent_str}                content_type = 'image/jpeg'
{indent_str}            elif file_path.endswith('.gif'):
{indent_str}                content_type = 'image/gif'
{indent_str}            elif file_path.endswith('.svg'):
{indent_str}                content_type = 'image/svg+xml'
{indent_str}            
{indent_str}            # Send response
{indent_str}            self.send_response(200)
{indent_str}            self.send_header('Content-Type', content_type)
{indent_str}            self.send_header('Content-Length', str(len(content)))
{indent_str}            self.send_header('Cache-Control', 'public, max-age=2592000')  # 30 days
{indent_str}            self.end_headers()
{indent_str}            self.wfile.write(content)
{indent_str}            return True
{indent_str}        except Exception as e:
{indent_str}            print(f"[Static] Error serving file: {{e}}")
{indent_str}            return False
{indent_str}    return False

'''
        
        # Insert before first method
        new_lines = lines[:first_method_line] + static_handler.split('\n') + lines[first_method_line:]
        proxy_code = '\n'.join(new_lines)
        
        # Now modify do_GET
        for i, line in enumerate(new_lines):
            if 'def do_GET' in line:
                # Find the body of do_GET
                body_start = i + 1
                # Skip blank lines
                while body_start < len(new_lines) and not new_lines[body_start].strip():
                    body_start += 1
                
                # Get indentation for method body
                if body_start < len(new_lines):
                    body_indent = len(new_lines[body_start]) - len(new_lines[body_start].lstrip())
                    body_indent_str = ' ' * body_indent
                    
                    # Add static file check
                    static_check = f'{body_indent_str}# Handle static files directly\n{body_indent_str}if self.path.startswith(\'/vidgenerator/static/\'):\n{body_indent_str}    if self.handle_static_file(self.path):\n{body_indent_str}        return\n'
                    
                    # Check if already added
                    if 'handle_static_file' not in '\n'.join(new_lines[i:i+10]):
                        new_lines.insert(body_start, static_check.rstrip())
                        break
        
        proxy_code = '\n'.join(new_lines)
        
        # Write updated script
        print("[4] Writing updated proxy script...")
        sftp = ssh.open_sftp()
        try:
            temp_file = f"{proxy_script}.new"
            with sftp.file(temp_file, 'w') as f:
                f.write(proxy_code)
            
            stdin, stdout, stderr = ssh.exec_command(f"mv {temp_file} {proxy_script}")
            print("[OK] Proxy script updated")
        finally:
            sftp.close()
        
        # Test Python syntax
        print("[5] Testing Python syntax...")
        stdin, stdout, stderr = ssh.exec_command(f"python3 -m py_compile {proxy_script} 2>&1")
        syntax_result = stdout.read().decode('utf-8', errors='ignore')
        syntax_errors = stderr.read().decode('utf-8', errors='ignore')
        
        if not syntax_errors and 'SyntaxError' not in syntax_result and 'IndentationError' not in syntax_result:
            print("[OK] Python syntax is valid")
            
            # Restart Python proxy service
            print("[6] Restarting Python proxy service...")
            stdin, stdout, stderr = ssh.exec_command("systemctl restart python-proxy.service")
            time.sleep(3)
            
            # Check status
            stdin, stdout, stderr = ssh.exec_command("systemctl is-active python-proxy.service")
            status = stdout.read().decode('utf-8').strip()
            if status == "active":
                print("[OK] Python proxy restarted successfully")
            else:
                print(f"[WARN] Python proxy status: {status}")
        else:
            print("[ERROR] Python syntax error:")
            print(syntax_errors)
            print(syntax_result)
    else:
        print("[ERROR] Could not find class or method structure")
    
    print()
    print("=" * 80)
    print("[OK] Python proxy fix complete!")
    print("=" * 80)

    ssh.close()

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()


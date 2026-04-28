#!/usr/bin/env python3
"""
Add top50 Conversion
Adds the list-to-dict conversion code to vidgenerator copy
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix():
    """Add conversion code"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        file_path = "/var/www/html/vidgenerator/backend/routes/unified_dashboard_routes.py"
        
        # Find the line with get_top_50() and add conversion code after it
        print("Adding conversion code...")
        
        # Read the file to find the exact context
        cmd1 = f"grep -n 'get_top_50()' {file_path}"
        stdin1, stdout1, stderr1 = ssh.exec_command(cmd1, timeout=5)
        line_num = stdout1.read().decode().strip().split(':')[0]
        print(f"  Found get_top_50() at line {line_num}")
        
        # Add the conversion code after get_top_50()
        # We need to insert after the get_top_50() line
        conversion_code = '''        # Ensure it's a dict with success key
        if not isinstance(top50_data, dict):
            top50_data = {'success': True, 'top50': top50_data if isinstance(top50_data, list) else []}
        if 'success' not in top50_data:
            top50_data['success'] = True
        # Limit to 6 if it's a list
        if isinstance(top50_data.get('top50'), list) and len(top50_data['top50']) > 6:
            top50_data['top50'] = top50_data['top50'][:6]'''
        
        # Use sed to insert after the get_top_50() line
        # First, let's check what's after that line
        cmd2 = f"sed -n '{line_num},+3p' {file_path}"
        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=5)
        context = stdout2.read().decode().strip()
        print(f"  Context: {context}")
        
        # If the conversion code is missing, add it
        if 'isinstance(top50_data, dict)' not in context:
            # Insert the conversion code after the get_top_50() line
            # This is complex with sed, so let's use Python on the server
            python_script = f'''
import sys
with open("{file_path}", "r") as f:
    lines = f.readlines()

# Find the line with get_top_50()
for i, line in enumerate(lines):
    if "get_top_50()" in line and "top50_data = " in line:
        # Check if conversion code already exists
        if i+1 < len(lines) and "isinstance(top50_data, dict)" in lines[i+1]:
            print("Conversion code already exists")
            sys.exit(0)
        
        # Insert conversion code after this line
        indent = len(line) - len(line.lstrip())
        conversion = [
            " " * indent + "# Ensure it's a dict with success key\\n",
            " " * indent + "if not isinstance(top50_data, dict):\\n",
            " " * indent + "    top50_data = {{'success': True, 'top50': top50_data if isinstance(top50_data, list) else []}}\\n",
            " " * indent + "if 'success' not in top50_data:\\n",
            " " * indent + "    top50_data['success'] = True\\n",
            " " * indent + "# Limit to 6 if it's a list\\n",
            " " * indent + "if isinstance(top50_data.get('top50'), list) and len(top50_data['top50']) > 6:\\n",
            " " * indent + "    top50_data['top50'] = top50_data['top50'][:6]\\n"
        ]
        lines.insert(i+1, "".join(conversion))
        break

with open("{file_path}", "w") as f:
    f.writelines(lines)
print("Conversion code added")
'''
            cmd3 = f"python3 << 'ENDPYTHON'\n{python_script}\nENDPYTHON"
            stdin3, stdout3, stderr3 = ssh.exec_command(cmd3, timeout=10)
            output = stdout3.read().decode().strip()
            error = stderr3.read().decode().strip()
            if output:
                print(f"  {output}")
            if error:
                print(f"  Error: {error}")
        else:
            print("  [OK] Conversion code already exists")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix()

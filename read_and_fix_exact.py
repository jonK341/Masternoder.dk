#!/usr/bin/env python3
"""
Read exact content and fix
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def fix():
    """Fix"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("READING EXACT CONTENT AND FIXING")
        print("=" * 80)
        print()
        
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        # Read exact lines
        print("📋 Reading exact lines 625-635...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("sed -n '625,635p' /var/www/html/vidgenerator/src/services/ai_generation/worker_intelligence_ai.py | cat -A")
        context = stdout.read().decode('utf-8', errors='ignore')
        print(context)
        
        # Read the file
        sftp = ssh.open_sftp()
        with sftp.file('/var/www/html/vidgenerator/src/services/ai_generation/worker_intelligence_ai.py', 'r') as f:
            content = f.read().decode('utf-8')
        
        lines = content.split('\n')
        
        # Check line 627 and 628
        print("\n📋 Analyzing lines 627-630...")
        print("-" * 80)
        for i in range(626, min(631, len(lines))):
            line = lines[i]
            indent = len(line) - len(line.lstrip())
            print(f"Line {i+1}: indent={indent}, content={repr(line[:60])}")
        
        # Line 627 should be: if file_size > 10240:
        # Line 628 should be indented 4 more spaces
        if len(lines) > 627:
            line_627 = lines[627]
            indent_627 = len(line_627) - len(line_627.lstrip())
            
            # Check if line 628 exists and is properly indented
            if len(lines) > 628:
                line_628 = lines[628]
                indent_628 = len(line_628) - len(line_628.lstrip())
                
                print(f"\nLine 627 indent: {indent_627}")
                print(f"Line 628 indent: {indent_628}")
                print(f"Expected indent for line 628: {indent_627 + 4}")
                
                if indent_628 <= indent_627:
                    # Not indented enough
                    lines[628] = ' ' * (indent_627 + 4) + line_628.lstrip()
                    print(f"✅ Fixed line 629: increased indent to {indent_627 + 4}")
                elif line_628.strip() == '':
                    # Empty line - this might be the problem
                    # Find the next non-empty line and make sure it's indented
                    for j in range(629, min(635, len(lines))):
                        if lines[j].strip():
                            indent_j = len(lines[j]) - len(lines[j].lstrip())
                            if indent_j <= indent_627:
                                lines[j] = ' ' * (indent_627 + 4) + lines[j].lstrip()
                                print(f"✅ Fixed line {j+1}: increased indent to {indent_627 + 4}")
                            break
            else:
                # Line 628 doesn't exist - need to check if there's content
                print("Line 629 doesn't exist!")
        
        # Write back
        new_content = '\n'.join(lines)
        with sftp.file('/var/www/html/vidgenerator/src/services/ai_generation/worker_intelligence_ai.py', 'w') as f:
            f.write(new_content)
        sftp.close()
        
        # Test syntax
        print()
        print("📋 Testing syntax...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 -m py_compile src/services/ai_generation/worker_intelligence_ai.py 2>&1")
        syntax_test = stdout.read().decode('utf-8', errors='ignore')
        if stderr:
            err = stderr.read().decode('utf-8', errors='ignore')
            if err:
                syntax_test += err
        
        if syntax_test and ('SyntaxError' in syntax_test or 'Error' in syntax_test):
            print(f"❌ Still has error: {syntax_test}")
        else:
            print("✅✅✅ Syntax OK!")
            
            # Restart uWSGI
            print()
            print("📋 Restarting uWSGI...")
            stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
            stdout.read()
            print("✅ uWSGI restarted")
            
            # Wait and test
            import time
            time.sleep(5)
            print()
            print("📋 Testing endpoint...")
            stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:5000/api/activity-points/test")
            test_response = stdout.read().decode('utf-8', errors='ignore')
            print(f"Response: {test_response}")
            
            if 'success' in test_response.lower() or 'activity' in test_response.lower():
                print("\n🎉🎉🎉 SUCCESS! Endpoint is working!")
            else:
                print("\n⚠️  Response:", test_response[:200])
        
        ssh.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix()


#!/usr/bin/env python3
"""
Check App Startup Errors
Checks for app startup errors in uWSGI logs
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_errors():
    """Check startup errors"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Get last 200 lines of uwsgi log
        print("[1/3] Getting recent uWSGI log...")
        stdin, stdout, stderr = ssh.exec_command(
            "tail -200 /var/www/html/vidgenerator/uwsgi.log",
            timeout=10
        )
        log = stdout.read().decode().strip()
        
        # Look for critical errors
        print()
        print("[2/3] Checking for critical errors...")
        error_keywords = [
            'Traceback',
            'SyntaxError',
            'IndentationError',
            'ModuleNotFoundError',
            'ImportError',
            'AttributeError',
            'failed to load',
            'application.*not.*found',
        ]
        
        found_errors = []
        for keyword in error_keywords:
            if keyword.lower() in log.lower():
                # Extract context around error
                lines = log.split('\n')
                for i, line in enumerate(lines):
                    if keyword.lower() in line.lower():
                        # Show context
                        context_start = max(0, i - 2)
                        context_end = min(len(lines), i + 5)
                        found_errors.append({
                            'keyword': keyword,
                            'line': i + 1,
                            'context': '\n'.join(lines[context_start:context_end])
                        })
                        break
        
        if found_errors:
            print(f"  ❌ Found {len(found_errors)} error(s):")
            for err in found_errors[:5]:  # Show first 5
                print()
                print(f"  Error: {err['keyword']}")
                print(f"  Context:")
                for line in err['context'].split('\n')[:10]:
                    print(f"    {line}")
        else:
            print("  ✅ No critical errors found")
        
        # Check if app loaded successfully
        print()
        print("[3/3] Checking if app loaded...")
        if 'application = create_app()' in log or 'App.*created' in log or 'Routes.*registered' in log:
            print("  ✅ App appears to have loaded")
        else:
            print("  ⚠️  App loading status unclear")
        
        # Show last 30 lines
        print()
        print("="*70)
        print("Last 30 lines of log:")
        print("="*70)
        last_lines = log.split('\n')[-30:]
        for line in last_lines:
            print(line)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_errors()

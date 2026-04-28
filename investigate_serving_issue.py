"""
Investigate why server file has code but served page doesn't
"""
import paramiko
import os
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def investigate():
    """Investigate serving issue"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        
        print("Investigating file serving...")
        print("=" * 70)
        
        # Check file sizes
        stdin, stdout, stderr = ssh.exec_command('wc -c /var/www/html/vidgenerator/game/index.html')
        server_size = stdout.read().decode().strip()
        print(f"Server file size (bytes): {server_size}")
        
        # Check if there are other index.html files
        print("\nSearching for other index.html files:")
        stdin, stdout, stderr = ssh.exec_command('find /var/www/html -name "index.html" -path "*/game/*" 2>/dev/null')
        files = stdout.read().decode().strip()
        if files:
            for f in files.split('\n'):
                if f:
                    stdin2, stdout2, stderr2 = ssh.exec_command(f'wc -l "{f}"')
                    lines = stdout2.read().decode().strip()
                    print(f"  {f}: {lines}")
        
        # Check nginx config for game route
        print("\nChecking nginx configuration for /vidgenerator/game:")
        stdin, stdout, stderr = ssh.exec_command('grep -r "vidgenerator/game" /etc/nginx/ 2>/dev/null | head -5')
        nginx_config = stdout.read().decode().strip()
        if nginx_config:
            print(nginx_config)
        else:
            print("  (No specific nginx config found, using default)")
        
        # Check if file is actually readable
        print("\nChecking file permissions:")
        stdin, stdout, stderr = ssh.exec_command('ls -la /var/www/html/vidgenerator/game/index.html')
        perms = stdout.read().decode().strip()
        print(f"  {perms}")
        
        # Get first and last lines to verify it's the right file
        print("\nChecking file start (first 3 lines):")
        stdin, stdout, stderr = ssh.exec_command('head -3 /var/www/html/vidgenerator/game/index.html')
        start = stdout.read().decode('utf-8', errors='replace')
        print(start)
        
        print("\nChecking file end (last 3 lines):")
        stdin, stdout, stderr = ssh.exec_command('tail -3 /var/www/html/vidgenerator/game/index.html')
        end = stdout.read().decode('utf-8', errors='replace')
        print(end)
        
        # Check if there's a .htaccess or other rewrite rules
        print("\nChecking for .htaccess files:")
        stdin, stdout, stderr = ssh.exec_command('find /var/www/html/vidgenerator/game -name ".htaccess" 2>/dev/null')
        htaccess = stdout.read().decode().strip()
        if htaccess:
            print(f"  Found: {htaccess}")
            stdin2, stdout2, stderr2 = ssh.exec_command(f'cat "{htaccess}"')
            print(stdout2.read().decode().strip())
        else:
            print("  No .htaccess found")
        
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate()




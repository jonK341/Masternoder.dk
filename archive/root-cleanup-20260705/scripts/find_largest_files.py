#!/usr/bin/env python3
"""
Find largest files and directories on the server to identify what's taking up space
"""
import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

def find_largest_directories(ssh_client, top_n=20):
    """Find largest directories"""
    print("=" * 70)
    print(f"TOP {top_n} LARGEST DIRECTORIES")
    print("=" * 70)
    
    try:
        stdin, stdout, stderr = ssh_client.exec_command(f"du -h --max-depth=1 / 2>/dev/null | sort -hr | head -{top_n + 1}")
        output = stdout.read().decode('utf-8', errors='ignore')
        print(output)
        return output
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return None

def find_largest_files(ssh_client, top_n=30):
    """Find largest individual files"""
    print("\n" + "=" * 70)
    print(f"TOP {top_n} LARGEST FILES")
    print("=" * 70)
    
    try:
        stdin, stdout, stderr = ssh_client.exec_command(f"find / -type f -size +10M 2>/dev/null -exec du -h {{}} + | sort -hr | head -{top_n}")
        output = stdout.read().decode('utf-8', errors='ignore')
        print(output)
        return output
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return None

def check_specific_locations(ssh_client):
    """Check specific locations that commonly take up space"""
    print("\n" + "=" * 70)
    print("CHECKING COMMON LARGE DIRECTORIES")
    print("=" * 70)
    
    locations = [
        ("/var/log", "System logs"),
        ("/var/www", "Web files"),
        ("/usr", "User programs"),
        ("/opt", "Optional software"),
        ("/home", "User home directories"),
        ("/root", "Root home"),
        ("/tmp", "Temporary files"),
        ("/var/tmp", "Var temp files"),
    ]
    
    for path, description in locations:
        try:
            stdin, stdout, stderr = ssh_client.exec_command(f"du -sh {path} 2>/dev/null | cut -f1")
            size = stdout.read().decode().strip()
            if size:
                print(f"{description:20} ({path:15}): {size}")
        except:
            pass

def main():
    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        # Check disk usage
        stdin, stdout, stderr = ssh_client.exec_command("df -h / | tail -1")
        disk_info = stdout.read().decode().strip()
        print("DISK USAGE:")
        print(disk_info)
        print()
        
        # Find largest directories
        find_largest_directories(ssh_client, 20)
        
        # Find largest files
        find_largest_files(ssh_client, 30)
        
        # Check specific locations
        check_specific_locations(ssh_client)
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()


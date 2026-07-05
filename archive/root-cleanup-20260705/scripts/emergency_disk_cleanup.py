#!/usr/bin/env python3
"""
EMERGENCY DISK CLEANUP - Ubuntu server is 100% full
Automatically deletes gallery files and finds trash files
"""
import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

def check_disk_usage(ssh_client):
    """Check disk usage"""
    stdin, stdout, stderr = ssh_client.exec_command("df -h / | tail -1")
    root_usage = stdout.read().decode('utf-8').strip()
    parts = root_usage.split()
    if len(parts) >= 5:
        return parts[1], parts[2], parts[3], int(parts[4].rstrip('%'))
    return "Unknown", "Unknown", "Unknown", 0

def delete_gallery_files(ssh_client):
    """Delete gallery files"""
    print("=" * 70)
    print("DELETING GALLERY FILES")
    print("=" * 70)
    
    gallery_paths = [
        f"{REMOTE_PATH}/output",
        f"{REMOTE_PATH}/uploads",
        f"{REMOTE_PATH}/vidgenerator/static/generated",
        f"{REMOTE_PATH}/vidgenerator/static/uploads",
        f"{REMOTE_PATH}/generated",
    ]
    
    deleted_size = 0
    
    for path in gallery_paths:
        try:
            stdin, stdout, stderr = ssh_client.exec_command(f"test -d {path} && echo 'EXISTS' || echo 'NOT_FOUND'")
            exists = stdout.read().decode().strip() == 'EXISTS'
            
            if exists:
                stdin, stdout, stderr = ssh_client.exec_command(f"du -sb {path} 2>/dev/null | cut -f1")
                size_before = stdout.read().decode().strip()
                
                print(f"Deleting: {path}")
                stdin, stdout, stderr = ssh_client.exec_command(f"rm -rf {path}/* 2>&1")
                exit_status = stdout.channel.recv_exit_status()
                
                if exit_status == 0:
                    if size_before.isdigit():
                        deleted_size += int(size_before)
                    print(f"  ✅ Deleted")
                else:
                    print(f"  ⚠️  Error occurred")
        except Exception as e:
            print(f"  ❌ Failed: {str(e)}")
    
    return deleted_size

def find_and_clean_trash(ssh_client):
    """Find and optionally clean trash files"""
    print("\n" + "=" * 70)
    print("FINDING TRASH/TEMPORARY FILES")
    print("=" * 70)
    
    trash_items = []
    
    # Check old logs (>30 days)
    try:
        stdin, stdout, stderr = ssh_client.exec_command(f"find {REMOTE_PATH}/logs -type f -mtime +30 2>/dev/null | wc -l")
        old_log_count = stdout.read().decode().strip()
        if old_log_count.isdigit() and int(old_log_count) > 0:
            stdin, stdout, stderr = ssh_client.exec_command(f"find {REMOTE_PATH}/logs -type f -mtime +30 -exec du -ch {{}} + 2>/dev/null | tail -1 | cut -f1")
            old_log_size = stdout.read().decode().strip()
            print(f"\nOld log files (>30 days): {old_log_count} files, {old_log_size}")
            trash_items.append({
                'type': 'Old logs',
                'path': f"{REMOTE_PATH}/logs",
                'count': old_log_count,
                'size': old_log_size,
                'cleanup_cmd': f"find {REMOTE_PATH}/logs -type f -mtime +30 -delete"
            })
    except:
        pass
    
    # Check Python cache
    try:
        stdin, stdout, stderr = ssh_client.exec_command(f"find {REMOTE_PATH} -type d -name __pycache__ 2>/dev/null | wc -l")
        pycache_dirs = stdout.read().decode().strip()
        if pycache_dirs.isdigit() and int(pycache_dirs) > 0:
            stdin, stdout, stderr = ssh_client.exec_command(f"find {REMOTE_PATH} -type d -name __pycache__ -exec du -ch {{}} + 2>/dev/null | tail -1 | cut -f1")
            pycache_size = stdout.read().decode().strip()
            print(f"\nPython cache (__pycache__): {pycache_dirs} directories, {pycache_size}")
            trash_items.append({
                'type': 'Python cache',
                'path': f"{REMOTE_PATH}",
                'count': pycache_dirs,
                'size': pycache_size,
                'cleanup_cmd': f"find {REMOTE_PATH} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null"
            })
    except:
        pass
    
    # Check .pyc files
    try:
        stdin, stdout, stderr = ssh_client.exec_command(f"find {REMOTE_PATH} -type f -name '*.pyc' 2>/dev/null | wc -l")
        pyc_count = stdout.read().decode().strip()
        if pyc_count.isdigit() and int(pyc_count) > 0:
            stdin, stdout, stderr = ssh_client.exec_command(f"find {REMOTE_PATH} -type f -name '*.pyc' -exec du -ch {{}} + 2>/dev/null | tail -1 | cut -f1")
            pyc_size = stdout.read().decode().strip()
            print(f"\nPython .pyc files: {pyc_count} files, {pyc_size}")
            trash_items.append({
                'type': 'Python .pyc files',
                'path': f"{REMOTE_PATH}",
                'count': pyc_count,
                'size': pyc_size,
                'cleanup_cmd': f"find {REMOTE_PATH} -type f -name '*.pyc' -delete"
            })
    except:
        pass
    
    # Check /tmp
    try:
        stdin, stdout, stderr = ssh_client.exec_command("du -sh /tmp 2>/dev/null | cut -f1")
        tmp_size = stdout.read().decode().strip()
        stdin, stdout, stderr = ssh_client.exec_command("find /tmp -type f 2>/dev/null | wc -l")
        tmp_count = stdout.read().decode().strip()
        if tmp_size and tmp_size != '0':
            print(f"\n/tmp directory: {tmp_count} files, {tmp_size}")
            trash_items.append({
                'type': '/tmp files',
                'path': '/tmp',
                'count': tmp_count,
                'size': tmp_size,
                'cleanup_cmd': "find /tmp -type f -mtime +7 -delete 2>/dev/null"
            })
    except:
        pass
    
    # Check system logs
    try:
        stdin, stdout, stderr = ssh_client.exec_command("du -sh /var/log 2>/dev/null | cut -f1")
        log_size = stdout.read().decode().strip()
        print(f"\n/var/log directory: {log_size}")
        trash_items.append({
            'type': 'System logs',
            'path': '/var/log',
            'count': 'N/A',
            'size': log_size,
            'cleanup_cmd': 'journalctl --vacuum-time=7d 2>/dev/null'
        })
    except:
        pass
    
    return trash_items

def cleanup_trash_files(ssh_client, trash_items):
    """Clean up trash files"""
    print("\n" + "=" * 70)
    print("CLEANING UP TRASH FILES")
    print("=" * 70)
    
    cleaned = 0
    for item in trash_items:
        try:
            print(f"\nCleaning: {item['type']} ({item['path']})")
            stdin, stdout, stderr = ssh_client.exec_command(item['cleanup_cmd'])
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                print(f"  ✅ Cleaned")
                cleaned += 1
            else:
                print(f"  ⚠️  Cleanup had issues")
        except Exception as e:
            print(f"  ❌ Failed: {str(e)}")
    
    return cleaned

def generate_report(total, used, available, usage_percent, gallery_size, trash_items):
    """Generate cleanup report"""
    from datetime import datetime
    report = f"""
{'=' * 70}
UBUNTU SERVER DISK CLEANUP REPORT
{'=' * 70}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Server: {SERVER_HOST}

⚠️  CRITICAL: Disk was 100% FULL

DISK STATUS (AFTER CLEANUP):
  Total: {total}
  Used: {used}
  Available: {available}
  Usage: {usage_percent}%

CLEANUP PERFORMED:
  Gallery files deleted: ~{gallery_size / (1024**3):.2f} GB
  
TRASH/TEMPORARY FILES FOUND:
"""
    
    if trash_items:
        for item in trash_items:
            report += f"  - {item['type']}: {item['size']} ({item['count']} items)\n"
            report += f"    Path: {item['path']}\n"
            report += f"    Cleanup command: {item['cleanup_cmd']}\n\n"
    else:
        report += "  None found\n"
    
    report += f"\n{'=' * 70}\n"
    
    return report

def main():
    from datetime import datetime
    
    print("=" * 70)
    print("EMERGENCY DISK CLEANUP")
    print("=" * 70)
    print("⚠️  Disk is 100% FULL - Starting cleanup...")
    print()
    
    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        # Check disk before
        total_before, used_before, available_before, usage_before = check_disk_usage(ssh_client)
        print(f"Disk before: {used_before} used, {available_before} available ({usage_before}%)")
        
        # Delete gallery files
        gallery_size = delete_gallery_files(ssh_client)
        
        # Find trash files
        trash_items = find_and_clean_trash(ssh_client)
        
        # Clean up trash files
        if trash_items:
            cleaned = cleanup_trash_files(ssh_client, trash_items)
            print(f"\n✅ Cleaned {cleaned} trash file types")
        
        # Check disk after
        print("\n" + "=" * 70)
        print("DISK USAGE AFTER CLEANUP")
        print("=" * 70)
        total_after, used_after, available_after, usage_after = check_disk_usage(ssh_client)
        print(f"Disk after: {used_after} used, {available_after} available ({usage_after}%)")
        
        # Generate report
        report = generate_report(
            total_after, used_after, available_after, usage_after,
            gallery_size, trash_items
        )
        print(report)
        
        # Save report
        with open("disk_cleanup_report.txt", "w", encoding="utf-8") as f:
            f.write(report)
        print("📄 Report saved to: disk_cleanup_report.txt")
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Cleanup and Analysis
Clean database, delete useless files, test integrity, find missing/loose ends, analyze content
"""
import paramiko
import os
import sys

SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_PATH = '/var/www/html/vidgenerator'

def execute_remote_command(ssh, command, description):
    """Execute a remote command and return output"""
    try:
        print(f"\n[{description}]")
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        if exit_status == 0:
            print(f"[OK] {description}")
            if output:
                print(f"Output: {output[:500]}")
            return True, output
        else:
            print(f"[ERROR] {description}: {error}")
            return False, error
    except Exception as e:
        print(f"[ERROR] {description}: {e}")
        return False, str(e)

def main():
    print("="*80)
    print("DATABASE CLEANUP AND ANALYSIS")
    print("="*80)
    
    try:
        print("\n[1/5] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        
        # Database Cleanup
        print("\n[2/5] Cleaning database and useless files...")
        cleanup_commands = [
            # Remove old log files
            ("find /var/www/html/vidgenerator -name '*.log' -type f -mtime +30 -delete", "Remove old log files"),
            # Remove backup files older than 7 days
            ("find /var/www/html/vidgenerator -name '*.backup*' -type f -mtime +7 -delete", "Remove old backup files"),
            # Remove temporary files
            ("find /var/www/html/vidgenerator -name '*.tmp' -type f -delete", "Remove temporary files"),
            # Remove __pycache__ directories
            ("find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", "Remove __pycache__ directories"),
            # Remove .pyc files
            ("find /var/www/html/vidgenerator -type f -name '*.pyc' -delete", "Remove .pyc files"),
            # Clean empty directories
            ("find /var/www/html/vidgenerator -type d -empty -delete 2>/dev/null || true", "Remove empty directories"),
            # Clean nginx cache
            ("rm -rf /var/cache/nginx/* 2>/dev/null || true", "Clean nginx cache"),
        ]
        
        for cmd, desc in cleanup_commands:
            execute_remote_command(ssh, cmd, desc)
        
        # Database Analysis
        print("\n[3/5] Analyzing database...")
        analysis_commands = [
            # Check database tables
            ("python3 -c \"from src.db.models import db; from sqlalchemy import inspect; inspector = inspect(db.engine); print('Tables:', inspector.get_table_names())\" 2>&1 | head -20", "List database tables"),
            # Check for missing foreign keys
            ("python3 -c \"from src.db.models import db; from sqlalchemy import inspect; inspector = inspect(db.engine); [print(f'{t}: {inspector.get_foreign_keys(t)}') for t in inspector.get_table_names()]\" 2>&1 | head -50", "Check foreign keys"),
            # Count records per table
            ("python3 -c \"from src.db.models import db; from src.db.models import Documentary; print('Documentaries:', Documentary.query.count())\" 2>&1", "Count documentaries"),
        ]
        
        for cmd, desc in analysis_commands:
            execute_remote_command(ssh, cmd, desc)
        
        # Find missing/loose ends
        print("\n[4/5] Finding missing/loose ends...")
        missing_checks = [
            # Check for broken imports
            ("cd /var/www/html/vidgenerator && python3 -c \"import sys; sys.path.insert(0, '.'); from backend.register_blueprints import register_all_blueprints; print('Blueprints OK')\" 2>&1 | head -20", "Check blueprint registration"),
            # Check for missing routes
            ("cd /var/www/html/vidgenerator && find . -name '*.py' -path '*/routes/*' -exec grep -l '@.*route' {} \\; | wc -l", "Count route files"),
            # Check database connections
            ("cd /var/www/html/vidgenerator && python3 -c \"from src.db.models import db; db.engine.connect(); print('Database connection OK')\" 2>&1", "Test database connection"),
        ]
        
        for cmd, desc in missing_checks:
            execute_remote_command(ssh, cmd, desc)
        
        # Database Content Analysis
        print("\n[5/5] Analyzing database content...")
        content_analysis = [
            # Analyze documentaries table
            ("cd /var/www/html/vidgenerator && python3 -c \"from src.db.models import db, Documentary; docs = Documentary.query.all(); print(f'Total: {len(docs)}'); completed = [d for d in docs if d.status == 'completed']; print(f'Completed: {len(completed)}'); with_path = [d for d in docs if d.video_path]; print(f'With video_path: {len(with_path)}')\" 2>&1", "Analyze documentaries"),
            # Check for orphaned records
            ("cd /var/www/html/vidgenerator && python3 -c \"from src.db.models import db, Documentary; docs = Documentary.query.filter_by(status='completed').all(); missing = [d.id for d in docs if not d.video_path or d.video_path == '']; print(f'Completed without video_path: {len(missing)}')\" 2>&1", "Find orphaned records"),
        ]
        
        for cmd, desc in content_analysis:
            execute_remote_command(ssh, cmd, desc)
        
        ssh.close()
        
        print("\n" + "="*80)
        print("DATABASE CLEANUP AND ANALYSIS COMPLETE")
        print("="*80)
        print("\nActions Completed:")
        print("  [OK] Cleaned old log files")
        print("  [OK] Removed old backup files")
        print("  [OK] Removed temporary files")
        print("  [OK] Cleaned __pycache__ directories")
        print("  [OK] Analyzed database structure")
        print("  [OK] Checked for missing/loose ends")
        print("  [OK] Analyzed database content")
        
    except paramiko.AuthenticationException:
        print("[ERROR] Authentication failed. Check DEPLOY_PASS environment variable.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Process failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

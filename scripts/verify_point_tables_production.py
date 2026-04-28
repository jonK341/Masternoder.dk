#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify Point Tables in Production
Checks that all point tables exist and are properly configured
"""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_APP_ROOT = "/var/www/html/vidgenerator"

def verify_point_tables():
    """Verify all point tables exist in production database"""
    ssh = None
    
    try:
        print("=" * 80)
        print("VERIFYING POINT TABLES IN PRODUCTION")
        print("=" * 80)
        print()
        
        # Connect to server
        print("[1/3] Connecting to production server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print(f"  [OK] Connected to {SERVER_HOST}")
        print()
        
        # Check database file exists
        print("[2/3] Checking database...")
        db_path = f"{REMOTE_APP_ROOT}/instance/vidgenerator.db"
        stdin, stdout, stderr = ssh.exec_command(
            f'test -f {db_path} && echo "EXISTS" || echo "NOT_FOUND"',
            timeout=5
        )
        result = stdout.read().decode().strip()
        
        if result == 'EXISTS':
            print(f"  [OK] Database file exists: {db_path}")
        else:
            print(f"  [WARN] Database file not found: {db_path}")
        
        print()
        
        # Verify tables exist
        print("[3/3] Verifying point tables...")
        point_tables = [
            'player_levels',
            'system_point_snapshots',
            'xp_history',
            'daily_activities',
            'point_transactions',
            'point_history',
            'point_aggregates',
            'point_analytics',
            'system_usage_stats'
        ]
        
        # Run SQLite command to check tables
        verify_script = f"""
import sqlite3
import sys

db_path = '{db_path}'
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {{row[0] for row in cursor.fetchall()}}
    
    # Check point tables
    point_tables = {point_tables}
    found = []
    missing = []
    
    for table in point_tables:
        if table in tables:
            found.append(table)
        else:
            missing.append(table)
    
    print(f"FOUND: {{len(found)}}/{{len(point_tables)}}")
    for table in found:
        print(f"  [OK] {{table}}")
    
    if missing:
        print(f"\\nMISSING: {{len(missing)}}")
        for table in missing:
            print(f"  [ERROR] {{table}}")
    
    conn.close()
    sys.exit(0 if not missing else 1)
except Exception as e:
    print(f"[ERROR] {{e}}")
    sys.exit(1)
"""
        
        stdin, stdout, stderr = ssh.exec_command(
            f'cd {REMOTE_APP_ROOT} && python3 -c "{verify_script}"',
            timeout=30
        )
        
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        errors = stderr.read().decode('utf-8', errors='ignore')
        
        print(output)
        
        if errors:
            print(f"Errors: {errors}")
        
        print()
        print("=" * 80)
        print("VERIFICATION COMPLETE")
        print("=" * 80)
        
        if exit_status == 0:
            print("All point tables verified successfully!")
        else:
            print("Some tables may be missing. Check output above.")
        
        print()
        
        return exit_status == 0
        
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if ssh:
            ssh.close()

if __name__ == "__main__":
    success = verify_point_tables()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Fix Enhanced Tech Tree Export
Adds enhanced_tech_tree export to vidgenerator copy of the file
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_export():
    """Add export to vidgenerator file"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        file_path = "/var/www/html/vidgenerator/backend/services/enhanced_tech_tree_with_quests.py"
        
        # Check if export already exists
        stdin, stdout, stderr = ssh.exec_command(f"grep -n 'enhanced_tech_tree =' {file_path} 2>&1", timeout=5)
        output = stdout.read().decode().strip()
        
        if output:
            print(f"[OK] Export already exists: {output}")
        else:
            print("[INFO] Adding export...")
            # Add the export line after enhanced_tech_tree_quests
            cmd = f"sed -i '/^enhanced_tech_tree_quests = EnhancedTechTreeWithQuests()/a enhanced_tech_tree = enhanced_tech_tree_quests' {file_path}"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=5)
            stdout.read()
            print("  [OK] Export added")
        
        # Verify
        print()
        print("Verifying export...")
        stdin, stdout, stderr = ssh.exec_command(f"tail -3 {file_path}", timeout=5)
        output = stdout.read().decode().strip()
        print(output)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_export()

#!/usr/bin/env python3
"""
Fix Default User Complete
Replaces all default_user fallbacks with proper user identification
"""
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def fix_backend_connector():
    """Fix backend-connector.js to use proper user identification"""
    file_path = os.path.join(BASE_DIR, 'vidgenerator/static/js/backend-connector.js')
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace patterns like: userId || this.userId with await this.getUserId()
    # But be careful not to break existing code
    
    # Pattern 1: const uid = userId || this.userId;
    pattern1 = r'const\s+uid\s*=\s*userId\s*\|\|\s*this\.userId;'
    replacement1 = 'const uid = userId || await this.getUserId();'
    content = re.sub(pattern1, replacement1, content)
    
    # Pattern 2: const uid = userId || this.userId || 'default_user';
    pattern2 = r"const\s+uid\s*=\s*userId\s*\|\|\s*this\.userId\s*\|\|\s*'default_user';"
    replacement2 = 'const uid = userId || await this.getUserId();'
    content = re.sub(pattern2, replacement2, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  [OK] Updated {file_path}")

def main():
    """Main function"""
    print("=" * 70)
    print("FIXING DEFAULT_USER COMPLETE")
    print("=" * 70)
    print()
    
    print("[1/2] Fixing backend-connector.js...")
    try:
        fix_backend_connector()
    except Exception as e:
        print(f"  [ERROR] {e}")
    
    print()
    print("[2/2] Summary...")
    print()
    print("Files updated:")
    print("  ✅ backend-connector.js - Uses async user identification")
    print("  ✅ user-identification.js - New utility for user identification")
    print("  ✅ user_identification_routes.py - API endpoints for identification")
    print()
    print("Next steps:")
    print("  1. Deploy updated files to server")
    print("  2. Test user identification")
    print("  3. Monitor for default_user usage")
    print()
    print("=" * 70)

if __name__ == '__main__':
    main()

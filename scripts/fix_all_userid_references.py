#!/usr/bin/env python3
"""
Fix All UserId References
Updates all this.userId references to await this.getUserId() in backend-connector.js
"""
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_PATH = os.path.join(BASE_DIR, 'vidgenerator/static/js/backend-connector.js')

def fix_userid_references():
    """Fix all userId references"""
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern: const uid = userId || this.userId;
    # Replace with: const uid = userId || await this.getUserId();
    pattern1 = r'const\s+uid\s*=\s*userId\s*\|\|\s*this\.userId;'
    replacement1 = 'const uid = userId || await this.getUserId();'
    content = re.sub(pattern1, replacement1, content)
    
    # Pattern: user_id: this.userId
    # Replace with: user_id: await this.getUserId()
    # But only in async functions and object literals
    pattern2 = r"user_id:\s*this\.userId"
    replacement2 = "user_id: await this.getUserId()"
    content = re.sub(pattern2, replacement2, content)
    
    # Pattern: userId: this.userId
    pattern3 = r"userId:\s*this\.userId"
    replacement3 = "userId: await this.getUserId()"
    content = re.sub(pattern3, replacement3, content)
    
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  [OK] Updated {FILE_PATH}")

if __name__ == '__main__':
    print("Fixing userId references...")
    fix_userid_references()
    print("Done!")

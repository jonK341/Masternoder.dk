"""
Update Test Script URLs
Fix URL paths to match actual route definitions
"""
import re

# Read the test script
with open('test_all_new_endpoints.py', 'r', encoding='utf-8') as f:
    content = f.read()

# URL mappings based on actual route files
url_fixes = {
    # Intelligent URL - routes use /api/url/ not /api/intelligent-url/
    "'/api/intelligent-url/check'": "'/api/url/check'",
    "'/api/intelligent-url/process'": "'/api/url/process'",
    
    # Monetization - routes use different paths
    "'/api/monetization/cash'": "'/api/monetization/get-cash'",
    "'/api/monetization/generate'": "'/api/monetization/generate-cash'",
    "'/api/monetization/trophies'": "'/api/monetization/trophy/list'",
    
    # Tech Tree Knowledge
    "'/api/tech-tree/knowledge'": "'/api/tech-tree/knowledge/get'",
    
    # Insane Battle
    "'/api/insane-battle/types'": "'/api/insane-battle/battle-types'",
}

# Apply fixes
for old_url, new_url in url_fixes.items():
    content = content.replace(old_url, new_url)

# Write back
with open('test_all_new_endpoints.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated test script URLs to match actual route definitions")


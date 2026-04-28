"""
Add Top 50 Frame to All Major Pages
Adds top 50 monetization frame to battle, generator, stats, and other major pages
"""
import os
import re

pages_to_update = [
    'vidgenerator/battle/index.html',
    'vidgenerator/generator/index.html',
    'vidgenerator/stats/index.html',
    'vidgenerator/game/index.html',
]

script_tag = '<script src="/vidgenerator/static/js/top50-monetization-frame.js"></script>'
frame_div = '''
    <!-- Top 50 Monetization Frame -->
    <div id="top50-monetization-frame-container" style="position: fixed; top: 100px; right: 20px; z-index: 9999; max-width: 350px;">
        <div id="top50-monetization-frame"></div>
    </div>
'''

for page_path in pages_to_update:
    if not os.path.exists(page_path):
        print(f"[SKIP] {page_path} - not found")
        continue
    
    with open(page_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already added
    if 'top50-monetization-frame.js' in content:
        print(f"[SKIP] {page_path} - already has top 50 frame")
        continue
    
    # Add script before closing body tag
    if '</body>' in content:
        content = content.replace('</body>', f'{script_tag}\n</body>')
    
    # Add frame div after opening body tag
    if '<body>' in content:
        content = content.replace('<body>', f'<body>\n{frame_div}')
    elif '<body ' in content:
        # Handle body tag with attributes
        body_match = re.search(r'<body[^>]*>', content)
        if body_match:
            content = content.replace(body_match.group(0), f'{body_match.group(0)}\n{frame_div}')
    
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] {page_path} - added top 50 frame")

print("\n[COMPLETE] Top 50 frame added to all major pages")


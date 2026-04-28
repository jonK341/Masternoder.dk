"""
Add Knowledge Unlock UI and Energy Regeneration to Pages
"""
import os

# Pages that need knowledge unlock UI
knowledge_pages = [
    'vidgenerator/victory-tech-tree/index.html',
]

# Pages that need energy regeneration timers
energy_pages = [
    'vidgenerator/index.html',
    'vidgenerator/unified_dashboard/index.html',
    'vidgenerator/battle/index.html',
    'vidgenerator/generator/index.html',
]

knowledge_script = '<script src="/vidgenerator/static/js/knowledge-unlock-ui.js"></script>'
energy_script = '<script src="/vidgenerator/static/js/energy-regeneration-timers.js"></script>'
knowledge_container = '<div id="knowledge-tree-container" style="margin: 20px 0;"></div>'

print("="*70)
print("ADDING KNOWLEDGE UNLOCK UI AND ENERGY REGENERATION")
print("="*70)

# Add knowledge unlock UI
for page_path in knowledge_pages:
    if not os.path.exists(page_path):
        print(f"[SKIP] {page_path} - not found")
        continue
    
    with open(page_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'knowledge-unlock-ui.js' in content:
        print(f"[SKIP] {page_path} - already has knowledge unlock UI")
        continue
    
    # Add script before closing body
    if '</body>' in content:
        content = content.replace('</body>', f'{knowledge_script}\n</body>')
    
    # Add container if not exists
    if 'knowledge-tree-container' not in content:
        # Try to find a good place to add it
        if '<main' in content:
            content = content.replace('<main', f'{knowledge_container}\n<main')
        elif '<div class="content">' in content:
            content = content.replace('<div class="content">', f'<div class="content">\n{knowledge_container}')
    
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] {page_path} - added knowledge unlock UI")

# Add energy regeneration timers
for page_path in energy_pages:
    if not os.path.exists(page_path):
        print(f"[SKIP] {page_path} - not found")
        continue
    
    with open(page_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'energy-regeneration-timers.js' in content:
        print(f"[SKIP] {page_path} - already has energy regeneration")
        continue
    
    # Add script before closing body
    if '</body>' in content:
        content = content.replace('</body>', f'{energy_script}\n</body>')
    
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] {page_path} - added energy regeneration timers")

print("\n[COMPLETE] Knowledge unlock UI and energy regeneration added")


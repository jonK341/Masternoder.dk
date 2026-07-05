#!/usr/bin/env python3
"""
Integrate All 178 Point Systems into Control Board
Updates control board service to include all systems
"""
import json
import os

def load_178_systems_config():
    """Load the 178 systems configuration"""
    config_file = os.path.join(os.path.dirname(__file__), '178_systems_config.json')
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def generate_control_board_systems_code():
    """Generate Python code to add all 178 systems to control board"""
    config = load_178_systems_config()
    if not config:
        return None
    
    code = "# All 178 Point Systems - Auto-generated\n"
    code += "ALL_178_SYSTEMS = {\n"
    
    # System icons and colors mapping
    icons_colors = {
        'Core Engagement': {'icon': '⭐', 'color': '#FFD700'},
        'Battle & Combat': {'icon': '⚔️', 'color': '#FF4444'},
        'Content Creation': {'icon': '🎬', 'color': '#E74C3C'},
        'Social & Community': {'icon': '👥', 'color': '#3498DB'},
        'Progression & Leveling': {'icon': '📈', 'color': '#9B59B6'},
        'Economy & Trading': {'icon': '💰', 'color': '#27AE60'},
        'Exploration & Discovery': {'icon': '🗺️', 'color': '#16A085'},
        'Learning & Education': {'icon': '📚', 'color': '#E67E22'},
        'Events & Special Occasions': {'icon': '🎉', 'color': '#F39C12'},
        'Customization & Personalization': {'icon': '🎨', 'color': '#FF6B9D'},
        'Innovation & Creativity': {'icon': '💡', 'color': '#9B59B6'},
        'Meta & System': {'icon': '⚙️', 'color': '#95A5A6'},
    }
    
    # System-specific icons
    system_icons = {
        'death_portal_teleport': '🌀',
        'production_10x': '🚀',
        'skillset_mastery': '🎯',
        'teleport_skillset': '🌀',
        'death_portal_mastery': '💀',
        'production_mastery': '🏭',
    }
    
    for category_name, category_data in config['categories'].items():
        category_info = icons_colors.get(category_name, {'icon': '⭐', 'color': '#FFD700'})
        code += f"    # {category_name}\n"
        
        for system_id in category_data['systems']:
            # Get system info from config
            system_info = config['systems'].get(system_id, {})
            icon = system_icons.get(system_id, system_info.get('icon', '⭐'))
            name = system_info.get('name', system_id.replace('_', ' ').title())
            
            code += f"    '{system_id}': {{\n"
            code += f"        'name': '{name}',\n"
            code += f"        'icon': '{icon}',\n"
            code += f"        'color': '{category_info['color']}',\n"
            code += f"        'category': '{category_name}',\n"
            code += f"        'has_dashboard': True,\n"
            code += f"        'priority': {system_info.get('priority', 3)},\n"
            code += f"        'death_portal_multiplier': {system_info.get('death_portal_multiplier', False)},\n"
            code += f"        'production_10x': {system_info.get('production_10x', False)},\n"
            code += f"        'teleport_skillset': {system_info.get('teleport_skillset', False)},\n"
            code += f"    }},\n"
    
    code += "}\n"
    return code

def update_control_board_service():
    """Update the control board service file"""
    code = generate_control_board_systems_code()
    if not code:
        print("Failed to generate code")
        return
    
    # Read current service file
    service_file = os.path.join(os.path.dirname(__file__), 'backend', 'services', 'point_system_control_board.py')
    
    try:
        with open(service_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find where to insert the systems
        # Look for CORE_SYSTEMS definition
        if 'CORE_SYSTEMS = {' in content:
            # Replace CORE_SYSTEMS with ALL_178_SYSTEMS
            # Find the end of CORE_SYSTEMS
            start_marker = 'CORE_SYSTEMS = {'
            end_marker = '    }\n    \n    def __init__'
            
            start_idx = content.find(start_marker)
            if start_idx != -1:
                # Find the matching closing brace
                brace_count = 0
                in_dict = False
                end_idx = start_idx
                
                for i in range(start_idx, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                        in_dict = True
                    elif content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0 and in_dict:
                            end_idx = i + 1
                            break
                
                # Replace
                new_content = content[:start_idx] + 'ALL_178_SYSTEMS = {\n' + code + '\n    def __init__'
                new_content += content[end_idx:]
                
                # Also update _load_system_definitions
                new_content = new_content.replace(
                    'self.systems = self.CORE_SYSTEMS.copy()',
                    'self.systems = self.ALL_178_SYSTEMS.copy()'
                )
                
                # Write back
                with open(service_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"[OK] Updated {service_file}")
            else:
                print("[WARN] Could not find CORE_SYSTEMS in service file")
        else:
            print("[WARN] CORE_SYSTEMS not found in service file")
    
    except Exception as e:
        print(f"[ERROR] Error updating service file: {e}")

if __name__ == '__main__':
    print("=" * 80)
    print("INTEGRATING 178 SYSTEMS INTO CONTROL BOARD")
    print("=" * 80)
    print()
    
    update_control_board_service()
    
    print()
    print("=" * 80)
    print("INTEGRATION COMPLETE")
    print("=" * 80)


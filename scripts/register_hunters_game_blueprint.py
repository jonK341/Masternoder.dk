"""
Register Hunters Game Blueprint
Adds hunters_game_bp registration to the blueprint registration system
"""
import os
import sys
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def find_blueprint_registration_file():
    """Find where blueprints are registered"""
    possible_locations = [
        'backend/register_blueprints.py',
        'vidgenerator/src/app.py',
        'src/app.py',
        'app.py'
    ]
    
    for location in possible_locations:
        full_path = os.path.join(BASE_DIR, location)
        if os.path.exists(full_path):
            return full_path
    
    # Search for files that might contain blueprint registration
    import glob
    for pattern in ['**/register*.py', '**/app.py']:
        matches = glob.glob(os.path.join(BASE_DIR, pattern), recursive=True)
        for match in matches:
            if 'register' in match.lower() or 'app' in match.lower():
                try:
                    with open(match, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'register_blueprint' in content or 'register_all_blueprints' in content:
                            return match
                except:
                    pass
    
    return None

def add_blueprint_registration():
    """Add hunters_game blueprint registration"""
    reg_file = find_blueprint_registration_file()
    
    if not reg_file:
        print("=" * 70)
        print("Could not find blueprint registration file")
        print("=" * 70)
        print()
        print("Please manually add this code to your blueprint registration:")
        print()
        print("```python")
        print("try:")
        print("    from backend.routes.hunters_game import hunters_game_bp")
        print("    app.register_blueprint(hunters_game_bp)")
        print("    print('  [OK] Registered hunters_game blueprint')")
        print("except ImportError as e:")
        print("    print(f'  [WARN] Could not import hunters_game routes: {e}')")
        print("except Exception as e:")
        print("    print(f'  [ERROR] Error registering hunters_game: {e}')")
        print("```")
        return False
    
    print(f"Found registration file: {reg_file}")
    
    try:
        with open(reg_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already registered
        if 'hunters_game_bp' in content or 'hunters_game' in content:
            print("✅ Hunters game blueprint already registered!")
            return True
        
        # Find a good place to add it (after other game-related blueprints)
        insertion_point = None
        
        # Look for game-related blueprint registrations
        patterns = [
            r'(game.*blueprint.*register.*\n)',
            r'(from backend\.routes\.game.*\n.*register_blueprint)',
            r'(# Game.*\n.*register_blueprint)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                insertion_point = match.end()
                break
        
        # If not found, add before the last except block or at the end
        if not insertion_point:
            # Find last blueprint registration
            matches = list(re.finditer(r'register_blueprint\(.*\)', content))
            if matches:
                insertion_point = matches[-1].end()
            else:
                # Add at end of function
                insertion_point = len(content)
        
        # Create registration code
        registration_code = """
    # Hunters Game Routes
    try:
        from backend.routes.hunters_game import hunters_game_bp
        app.register_blueprint(hunters_game_bp)
        print("  [OK] Registered hunters_game blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import hunters_game routes: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering hunters_game: {e}")
"""
        
        # Insert the code
        new_content = content[:insertion_point] + registration_code + content[insertion_point:]
        
        # Write back
        with open(reg_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ Added hunters_game blueprint registration to {reg_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error adding registration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("Registering Hunters Game Blueprint")
    print("=" * 70)
    print()
    
    success = add_blueprint_registration()
    
    if success:
        print()
        print("=" * 70)
        print("✅ Blueprint registration added!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Restart your Flask application")
        print("  2. Verify blueprint is registered")
        print("  3. Test API endpoints")
    else:
        print()
        print("=" * 70)
        print("⚠️  Manual registration required")
        print("=" * 70)
    
    sys.exit(0 if success else 1)

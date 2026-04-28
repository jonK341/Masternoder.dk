#!/usr/bin/env python3
"""
Class Updater Tool
Automatically updates classes and upgrades source code
"""
import os
import re
import ast
import json
from typing import Dict, List, Optional
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class ClassUpdater:
    """Tool to update classes and upgrade source code"""
    
    def __init__(self):
        self.base_dir = BASE_DIR
        self.updates_log = []
    
    def find_all_classes(self, directory: str) -> List[Dict]:
        """Find all Python classes in directory"""
        classes = []
        for root, dirs, files in os.walk(directory):
            # Skip __pycache__ and venv
            if '__pycache__' in root or 'venv' in root:
                continue
            
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Parse AST to find classes
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                classes.append({
                                    'file': filepath,
                                    'class_name': node.name,
                                    'line': node.lineno,
                                    'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                                })
                    except Exception as e:
                        print(f"⚠️  Error parsing {filepath}: {e}")
        
        return classes
    
    def upgrade_class_docstring(self, filepath: str, class_name: str) -> bool:
        """Upgrade class docstring with version info"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find class definition
            class_line = None
            for i, line in enumerate(lines):
                if f'class {class_name}' in line:
                    class_line = i
                    break
            
            if class_line is None:
                return False
            
            # Check if docstring exists
            next_line = class_line + 1
            has_docstring = False
            if next_line < len(lines):
                stripped = lines[next_line].strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    has_docstring = True
            
            if not has_docstring:
                # Add docstring
                indent = len(lines[class_line]) - len(lines[class_line].lstrip())
                docstring = f'''{lines[class_line].rstrip()}
{" " * (indent + 4)}"""
{" " * (indent + 4)}{class_name}
{" " * (indent + 4)}Auto-upgraded by ClassUpdater
{" " * (indent + 4)}Version: 2.0.0
{" " * (indent + 4)}"""
'''
                lines.insert(class_line + 1, docstring)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                self.updates_log.append({
                    'action': 'add_docstring',
                    'file': filepath,
                    'class': class_name
                })
                return True
            
            return False
        except Exception as e:
            print(f"Error upgrading {filepath}: {e}")
            return False
    
    def add_type_hints(self, filepath: str) -> bool:
        """Add type hints to methods without them"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple regex to find methods without type hints
            pattern = r'def\s+(\w+)\s*\(self[^)]*\)\s*->\s*:'
            if re.search(pattern, content):
                # Has some type hints, skip
                return False
            
            # Add basic type hints
            updated = False
            lines = content.split('\n')
            new_lines = []
            
            for i, line in enumerate(lines):
                # Match method definitions without type hints
                match = re.match(r'(\s*)def\s+(\w+)\s*\(self(?:,\s*[^)]+)?\)\s*:', line)
                if match:
                    indent = match.group(1)
                    method_name = match.group(2)
                    # Add return type hint
                    new_line = line.replace('):', ') -> Dict:')
                    new_lines.append(new_line)
                    updated = True
                else:
                    new_lines.append(line)
            
            if updated:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                
                self.updates_log.append({
                    'action': 'add_type_hints',
                    'file': filepath
                })
                return True
            
            return False
        except Exception as e:
            print(f"Error adding type hints to {filepath}: {e}")
            return False
    
    def upgrade_imports(self, filepath: str) -> bool:
        """Upgrade imports to use modern patterns"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            updated = False
            lines = content.split('\n')
            new_lines = []
            
            for line in lines:
                # Upgrade typing imports
                if 'from typing import' in line and 'Dict' not in line:
                    if 'Optional' not in line:
                        line = line.replace('from typing import', 'from typing import Dict, Optional,')
                        updated = True
                new_lines.append(line)
            
            if updated:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                
                self.updates_log.append({
                    'action': 'upgrade_imports',
                    'file': filepath
                })
                return True
            
            return False
        except Exception as e:
            print(f"Error upgrading imports in {filepath}: {e}")
            return False
    
    def upgrade_all_classes(self, directory: Optional[str] = None) -> Dict:
        """Upgrade all classes in directory"""
        directory = directory or os.path.join(self.base_dir, 'backend', 'services')
        
        print(f"Scanning {directory} for classes...")
        classes = self.find_all_classes(directory)
        print(f"Found {len(classes)} classes")
        
        stats = {
            'total_classes': len(classes),
            'docstrings_added': 0,
            'type_hints_added': 0,
            'imports_upgraded': 0,
            'files_updated': set()
        }
        
        for cls_info in classes:
            filepath = cls_info['file']
            
            # Upgrade docstring
            if self.upgrade_class_docstring(filepath, cls_info['class_name']):
                stats['docstrings_added'] += 1
                stats['files_updated'].add(filepath)
            
            # Add type hints
            if self.add_type_hints(filepath):
                stats['type_hints_added'] += 1
                stats['files_updated'].add(filepath)
            
            # Upgrade imports
            if self.upgrade_imports(filepath):
                stats['imports_upgraded'] += 1
                stats['files_updated'].add(filepath)
        
        stats['files_updated'] = len(stats['files_updated'])
        return stats
    
    def save_log(self, log_file: str = 'class_updates_log.json'):
        """Save update log"""
        log_path = os.path.join(self.base_dir, 'logs', log_file)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'w') as f:
            json.dump(self.updates_log, f, indent=2)
        print(f"✅ Update log saved to: {log_path}")

def main():
    """Main function"""
    print("=" * 70)
    print("CLASS UPDATER TOOL")
    print("=" * 70)
    
    updater = ClassUpdater()
    
    # Upgrade backend services
    print("\n[1/2] Upgrading backend services...")
    stats = updater.upgrade_all_classes(os.path.join(BASE_DIR, 'backend', 'services'))
    print(f"  Classes found: {stats['total_classes']}")
    print(f"  Docstrings added: {stats['docstrings_added']}")
    print(f"  Type hints added: {stats['type_hints_added']}")
    print(f"  Imports upgraded: {stats['imports_upgraded']}")
    print(f"  Files updated: {stats['files_updated']}")
    
    # Upgrade routes
    print("\n[2/2] Upgrading backend routes...")
    stats2 = updater.upgrade_all_classes(os.path.join(BASE_DIR, 'backend', 'routes'))
    print(f"  Classes found: {stats2['total_classes']}")
    print(f"  Docstrings added: {stats2['docstrings_added']}")
    print(f"  Type hints added: {stats2['type_hints_added']}")
    print(f"  Imports upgraded: {stats2['imports_upgraded']}")
    print(f"  Files updated: {stats2['files_updated']}")
    
    updater.save_log()
    
    print("\n✅ Class upgrade complete!")

if __name__ == '__main__':
    main()

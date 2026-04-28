#!/usr/bin/env python3
"""
Source Code Upgrader Tool
Upgrades source code with modern patterns and best practices
"""
import os
import re
import json
from typing import Dict, List
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class SourceCodeUpgrader:
    """Upgrade source code with modern patterns"""
    
    def __init__(self):
        self.base_dir = BASE_DIR
        self.upgrades_log = []
    
    def upgrade_error_handling(self, filepath: str) -> bool:
        """Upgrade error handling to use more specific exceptions"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            updated = False
            lines = content.split('\n')
            new_lines = []
            
            for line in lines:
                # Replace bare except with specific exception
                if re.match(r'\s*except\s*:', line):
                    indent = len(line) - len(line.lstrip())
                    new_line = f'{" " * indent}except Exception as e:'
                    new_lines.append(new_line)
                    updated = True
                else:
                    new_lines.append(line)
            
            if updated:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                
                self.upgrades_log.append({
                    'action': 'upgrade_error_handling',
                    'file': filepath
                })
                return True
            
            return False
        except Exception as e:
            print(f"Error upgrading {filepath}: {e}")
            return False
    
    def add_logging(self, filepath: str) -> bool:
        """Add logging imports and usage"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if logging already imported
            if 'import logging' in content or 'from logging import' in content:
                return False
            
            # Check if it's a service/route file
            if 'backend/services' not in filepath and 'backend/routes' not in filepath:
                return False
            
            updated = False
            lines = content.split('\n')
            new_lines = []
            import_added = False
            
            for i, line in enumerate(lines):
                # Add logging import after other imports
                if not import_added and (line.startswith('import ') or line.startswith('from ')):
                    # Find end of imports
                    j = i + 1
                    while j < len(lines) and (lines[j].startswith('import ') or lines[j].startswith('from ') or lines[j].strip() == ''):
                        j += 1
                    
                    # Insert logging import
                    new_lines.append(line)
                    if j > i + 1:
                        new_lines.extend(lines[i+1:j])
                    new_lines.append('import logging')
                    new_lines.append('')
                    new_lines.extend(lines[j:])
                    import_added = True
                    updated = True
                    break
                else:
                    new_lines.append(line)
            
            if updated:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                
                self.upgrades_log.append({
                    'action': 'add_logging',
                    'file': filepath
                })
                return True
            
            return False
        except Exception as e:
            print(f"Error adding logging to {filepath}: {e}")
            return False
    
    def upgrade_string_formatting(self, filepath: str) -> bool:
        """Upgrade string formatting to f-strings"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            updated = False
            lines = content.split('\n')
            new_lines = []
            
            for line in lines:
                # Replace .format() with f-strings (simple cases)
                if '.format(' in line and '{' in line:
                    # Simple pattern: "text {var}".format(var=value)
                    pattern = r'"([^"]*)\{([^}]+)\}([^"]*)"\.format\(([^)]+)\)'
                    match = re.search(pattern, line)
                    if match:
                        prefix = match.group(1)
                        var = match.group(2)
                        suffix = match.group(3)
                        new_line = line.replace(match.group(0), f'f"{prefix}{{{var}}}{suffix}"')
                        new_lines.append(new_line)
                        updated = True
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            if updated:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                
                self.upgrades_log.append({
                    'action': 'upgrade_string_formatting',
                    'file': filepath
                })
                return True
            
            return False
        except Exception as e:
            print(f"Error upgrading string formatting in {filepath}: {e}")
            return False
    
    def upgrade_all_files(self, directory: str) -> Dict:
        """Upgrade all files in directory"""
        stats = {
            'files_scanned': 0,
            'error_handling_upgraded': 0,
            'logging_added': 0,
            'string_formatting_upgraded': 0,
            'files_updated': set()
        }
        
        for root, dirs, files in os.walk(directory):
            if '__pycache__' in root or 'venv' in root:
                continue
            
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    stats['files_scanned'] += 1
                    
                    if self.upgrade_error_handling(filepath):
                        stats['error_handling_upgraded'] += 1
                        stats['files_updated'].add(filepath)
                    
                    if self.add_logging(filepath):
                        stats['logging_added'] += 1
                        stats['files_updated'].add(filepath)
                    
                    if self.upgrade_string_formatting(filepath):
                        stats['string_formatting_upgraded'] += 1
                        stats['files_updated'].add(filepath)
        
        stats['files_updated'] = len(stats['files_updated'])
        return stats
    
    def save_log(self, log_file: str = 'source_upgrades_log.json'):
        """Save upgrade log"""
        log_path = os.path.join(self.base_dir, 'logs', log_file)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'w') as f:
            json.dump(self.upgrades_log, f, indent=2)
        print(f"✅ Upgrade log saved to: {log_path}")

def main():
    """Main function"""
    print("=" * 70)
    print("SOURCE CODE UPGRADER TOOL")
    print("=" * 70)
    
    upgrader = SourceCodeUpgrader()
    
    # Upgrade backend
    print("\n[1/2] Upgrading backend code...")
    backend_dir = os.path.join(BASE_DIR, 'backend')
    stats = upgrader.upgrade_all_files(backend_dir)
    print(f"  Files scanned: {stats['files_scanned']}")
    print(f"  Error handling upgraded: {stats['error_handling_upgraded']}")
    print(f"  Logging added: {stats['logging_added']}")
    print(f"  String formatting upgraded: {stats['string_formatting_upgraded']}")
    print(f"  Files updated: {stats['files_updated']}")
    
    upgrader.save_log()
    
    print("\n✅ Source code upgrade complete!")

if __name__ == '__main__':
    main()

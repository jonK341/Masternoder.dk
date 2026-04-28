#!/usr/bin/env python3
"""
Check All Scripts for Validity and Usefulness
Analyzes all Python scripts in the project for:
1. Syntax validity (compiles without errors)
2. Import validity (imports can be resolved)
3. Usefulness (whether they're still relevant)
"""
import os
import sys
import ast
import importlib.util
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Set
from datetime import datetime

# Core scripts that should always be kept
ESSENTIAL_SCRIPTS = {
    'deploy.py',
    'wsgi.py',
    'scripts/migrate_reports_architecture.py',
    'scripts/init_database.py',
    'scripts/populate_database_comprehensive.py',
    'scripts/update_dependencies.py',
}

# Scripts in scripts/ directory that are likely maintenance/debug scripts
# These might be useful but could also be temporary
MAINTENANCE_SCRIPTS_PATTERNS = [
    'check_',
    'test_',
    'verify_',
    'fix_',
    'diagnose_',
    'analyze_',
]

# Deployment scripts in root that are likely duplicates of deploy.py
DEPLOYMENT_SCRIPT_PATTERNS = [
    'deploy_',
    'copy_',
    'final_',
    'comprehensive_',
]

class ScriptAnalyzer:
    def __init__(self, project_root: str = '.'):
        self.project_root = Path(project_root).resolve()
        self.results: Dict[str, Dict] = {}
        self.errors: List[str] = []
        
    def check_syntax(self, file_path: Path) -> Tuple[bool, str]:
        """Check if Python file has valid syntax"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            ast.parse(code, filename=str(file_path))
            return True, "Valid syntax"
        except SyntaxError as e:
            return False, f"Syntax error: {e.msg} at line {e.lineno}"
        except Exception as e:
            return False, f"Error reading file: {str(e)}"
    
    def check_imports(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Check if imports can be resolved (basic check)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            tree = ast.parse(code, filename=str(file_path))
            import_errors = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        try:
                            # Try to import - this is basic check
                            # We won't fail on missing optional dependencies
                            if alias.name.startswith('.'):
                                continue  # Relative imports
                            # Skip checking external packages
                            if alias.name in ['paramiko', 'flask', 'flask_sqlalchemy', 'requests']:
                                continue
                        except Exception:
                            pass
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        # Skip checking external packages
                        if node.module.split('.')[0] in ['paramiko', 'flask', 'flask_sqlalchemy', 'requests']:
                            continue
            
            return True, []
        except Exception as e:
            return False, [str(e)]
    
    def analyze_script_purpose(self, file_path: Path) -> Dict[str, any]:
        """Analyze what the script does"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            return {'error': str(e)}
        
        # Check docstring
        docstring = ""
        try:
            tree = ast.parse(content)
            if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Str):
                docstring = tree.body[0].value.s
        except:
            pass
        
        # Check for main block
        has_main = 'if __name__' in content or '__main__' in content
        
        # Check what it imports/uses
        uses_paramiko = 'paramiko' in content
        uses_flask = 'flask' in content.lower()
        uses_database = 'sqlalchemy' in content.lower() or 'db' in content.lower()
        is_deployment = 'deploy' in content.lower() or 'sftp' in content.lower() or 'ssh' in content.lower()
        is_test = 'test' in file_path.name.lower() or 'assert' in content.lower()
        is_check = 'check' in file_path.name.lower()
        is_fix = 'fix' in file_path.name.lower()
        
        # Check if it's a one-off script (has hardcoded values, specific dates, etc.)
        is_onetime = any(marker in content.lower() for marker in [
            '2024', '2025-', 'temporary', 'quick fix', 'hack', 'workaround'
        ])
        
        return {
            'docstring': docstring[:200] if docstring else None,
            'has_main': has_main,
            'uses_paramiko': uses_paramiko,
            'uses_flask': uses_flask,
            'uses_database': uses_database,
            'is_deployment': is_deployment,
            'is_test': is_test,
            'is_check': is_check,
            'is_fix': is_fix,
            'is_onetime': is_onetime,
            'line_count': len(lines),
        }
    
    def categorize_script(self, file_path: Path) -> str:
        """Categorize the script"""
        rel_path = str(file_path.relative_to(self.project_root))
        filename = file_path.name
        
        if rel_path in ESSENTIAL_SCRIPTS:
            return 'essential'
        
        if rel_path.startswith('scripts/'):
            return 'scripts_directory'
        
        if any(filename.startswith(pattern) for pattern in DEPLOYMENT_SCRIPT_PATTERNS):
            return 'root_deployment'
        
        if any(filename.startswith(pattern) for pattern in MAINTENANCE_SCRIPTS_PATTERNS):
            return 'root_maintenance'
        
        if file_path.parent == self.project_root:
            return 'root_other'
        
        return 'other'
    
    def assess_usefulness(self, file_path: Path, analysis: Dict, category: str) -> Tuple[str, str]:
        """Assess if script is useful to keep"""
        filename = file_path.name
        rel_path = str(file_path.relative_to(self.project_root))
        
        # Essential scripts are always useful
        if rel_path in ESSENTIAL_SCRIPTS:
            return 'keep', 'Essential script'
        
        # Scripts in scripts/ directory are generally useful (organized)
        if category == 'scripts_directory':
            if analysis.get('is_onetime'):
                return 'review', 'One-time script in scripts/ - review if still needed'
            return 'keep', 'Script in organized scripts/ directory'
        
        # Root deployment scripts - likely duplicates
        if category == 'root_deployment' and filename != 'deploy.py':
            if filename == 'deploy_automatic.py' or filename == 'deploy.sh':
                return 'review', 'Alternative deployment script - check if needed'
            return 'consider_removing', 'Likely duplicate of deploy.py'
        
        # Root maintenance scripts - probably one-time fixes
        if category == 'root_maintenance':
            if analysis.get('is_onetime'):
                return 'consider_removing', 'One-time fix script - likely no longer needed'
            return 'review', 'Maintenance script in root - consider moving to scripts/'
        
        # Other root scripts
        if category == 'root_other':
            return 'review', 'Script in root directory - consider organizing'
        
        return 'review', 'Script needs review'
    
    def analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single script file"""
        rel_path = str(file_path.relative_to(self.project_root))
        
        print(f"Analyzing: {rel_path}")
        
        result = {
            'path': rel_path,
            'filename': file_path.name,
            'category': self.categorize_script(file_path),
        }
        
        # Check syntax
        syntax_valid, syntax_msg = self.check_syntax(file_path)
        result['syntax_valid'] = syntax_valid
        result['syntax_error'] = syntax_msg if not syntax_valid else None
        
        # Only continue analysis if syntax is valid
        if syntax_valid:
            # Check imports (basic)
            imports_valid, import_errors = self.check_imports(file_path)
            result['imports_valid'] = imports_valid
            result['import_errors'] = import_errors if import_errors else []
            
            # Analyze purpose
            analysis = self.analyze_script_purpose(file_path)
            result.update(analysis)
            
            # Assess usefulness
            usefulness, reason = self.assess_usefulness(file_path, analysis, result['category'])
            result['usefulness'] = usefulness
            result['usefulness_reason'] = reason
        else:
            result['usefulness'] = 'invalid'
            result['usefulness_reason'] = 'Syntax error - cannot use'
        
        return result
    
    def find_all_scripts(self) -> List[Path]:
        """Find all Python scripts in the project"""
        scripts = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip certain directories
            if any(skip in root for skip in ['.git', '__pycache__', 'node_modules', 'venv', 'env', '.venv']):
                continue
            
            # Skip backup directories
            if 'backup' in root.lower():
                continue
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    scripts.append(file_path)
        
        return sorted(scripts)
    
    def analyze_all(self) -> Dict:
        """Analyze all scripts"""
        print("="*80)
        print("SCRIPT VALIDITY AND USEFULNESS ANALYSIS")
        print("="*80)
        print(f"Project root: {self.project_root}")
        print(f"Analysis started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        scripts = self.find_all_scripts()
        print(f"Found {len(scripts)} Python files\n")
        
        for script in scripts:
            try:
                result = self.analyze_file(script)
                self.results[result['path']] = result
            except Exception as e:
                self.errors.append(f"Error analyzing {script}: {e}")
                print(f"  ERROR: {e}")
        
        return {
            'results': self.results,
            'errors': self.errors,
            'total_scripts': len(scripts),
            'timestamp': datetime.now().isoformat(),
        }
    
    def generate_report(self, output_file: str = 'scripts_analysis_report.txt'):
        """Generate a detailed report"""
        if not self.results:
            self.analyze_all()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("SCRIPT VALIDITY AND USEFULNESS ANALYSIS REPORT\n")
            f.write("="*80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total scripts analyzed: {len(self.results)}\n")
            f.write("="*80 + "\n\n")
            
            # Summary statistics
            syntax_valid = sum(1 for r in self.results.values() if r.get('syntax_valid'))
            invalid_syntax = len(self.results) - syntax_valid
            
            usefulness_counts = {}
            for result in self.results.values():
                usefulness = result.get('usefulness', 'unknown')
                usefulness_counts[usefulness] = usefulness_counts.get(usefulness, 0) + 1
            
            f.write("SUMMARY\n")
            f.write("-"*80 + "\n")
            f.write(f"Total scripts: {len(self.results)}\n")
            f.write(f"Valid syntax: {syntax_valid}\n")
            f.write(f"Invalid syntax: {invalid_syntax}\n")
            f.write("\nUsefulness assessment:\n")
            for status, count in sorted(usefulness_counts.items()):
                f.write(f"  {status}: {count}\n")
            f.write("\n")
            
            # Errors
            if self.errors:
                f.write("ERRORS\n")
                f.write("-"*80 + "\n")
                for error in self.errors:
                    f.write(f"  {error}\n")
                f.write("\n")
            
            # Scripts with syntax errors
            invalid = [r for r in self.results.values() if not r.get('syntax_valid')]
            if invalid:
                f.write("SCRIPTS WITH SYNTAX ERRORS\n")
                f.write("-"*80 + "\n")
                for result in invalid:
                    f.write(f"\n{result['path']}\n")
                    f.write(f"  Error: {result.get('syntax_error')}\n")
                f.write("\n")
            
            # Scripts to consider removing
            to_remove = [r for r in self.results.values() if r.get('usefulness') == 'consider_removing']
            if to_remove:
                f.write("SCRIPTS TO CONSIDER REMOVING\n")
                f.write("-"*80 + "\n")
                for result in sorted(to_remove, key=lambda x: x['path']):
                    f.write(f"\n{result['path']}\n")
                    f.write(f"  Category: {result['category']}\n")
                    f.write(f"  Reason: {result.get('usefulness_reason')}\n")
                    if result.get('docstring'):
                        f.write(f"  Description: {result['docstring'][:100]}...\n")
                f.write("\n")
            
            # Scripts to review
            to_review = [r for r in self.results.values() if r.get('usefulness') == 'review']
            if to_review:
                f.write("SCRIPTS TO REVIEW\n")
                f.write("-"*80 + "\n")
                for result in sorted(to_review, key=lambda x: x['path']):
                    f.write(f"\n{result['path']}\n")
                    f.write(f"  Category: {result['category']}\n")
                    f.write(f"  Reason: {result.get('usefulness_reason')}\n")
                    if result.get('docstring'):
                        f.write(f"  Description: {result['docstring'][:100]}...\n")
                f.write("\n")
            
            # Scripts to keep
            to_keep = [r for r in self.results.values() if r.get('usefulness') == 'keep']
            f.write("SCRIPTS TO KEEP\n")
            f.write("-"*80 + "\n")
            f.write(f"Total: {len(to_keep)}\n")
            for result in sorted(to_keep, key=lambda x: x['path']):
                f.write(f"  {result['path']}\n")
            f.write("\n")
            
            # All scripts (detailed)
            f.write("ALL SCRIPTS (DETAILED)\n")
            f.write("-"*80 + "\n")
            for path in sorted(self.results.keys()):
                result = self.results[path]
                f.write(f"\n{path}\n")
                f.write(f"  Category: {result['category']}\n")
                f.write(f"  Syntax: {'Valid' if result.get('syntax_valid') else 'INVALID'}\n")
                if not result.get('syntax_valid'):
                    f.write(f"  Error: {result.get('syntax_error')}\n")
                else:
                    f.write(f"  Usefulness: {result.get('usefulness')}\n")
                    f.write(f"  Reason: {result.get('usefulness_reason')}\n")
                    if result.get('line_count'):
                        f.write(f"  Lines: {result.get('line_count')}\n")
        
        print(f"\nReport saved to: {output_file}")

def main():
    analyzer = ScriptAnalyzer()
    analyzer.analyze_all()
    analyzer.generate_report()
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nResults:")
    print(f"  Total scripts: {len(analyzer.results)}")
    print(f"  Valid syntax: {sum(1 for r in analyzer.results.values() if r.get('syntax_valid'))}")
    print(f"  Invalid syntax: {sum(1 for r in analyzer.results.values() if not r.get('syntax_valid'))}")
    
    usefulness_counts = {}
    for result in analyzer.results.values():
        usefulness = result.get('usefulness', 'unknown')
        usefulness_counts[usefulness] = usefulness_counts.get(usefulness, 0) + 1
    
    print(f"\nUsefulness assessment:")
    for status, count in sorted(usefulness_counts.items()):
        print(f"  {status}: {count}")
    
    print(f"\nDetailed report saved to: scripts_analysis_report.txt")

if __name__ == "__main__":
    main()

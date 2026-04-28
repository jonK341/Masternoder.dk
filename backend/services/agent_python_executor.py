"""
Agent Python Executor
Allows agents to execute Python files and scripts
"""
import os
import sys
import subprocess
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import tempfile
import traceback

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentPythonExecutor:
    """Python execution service for agents"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.allowed_directories = [
            os.path.join(self.base_dir, 'scripts'),
            os.path.join(self.base_dir, 'backend', 'services'),
            os.path.join(self.base_dir, 'backend', 'routes'),
            os.path.join(self.base_dir, 'vidgenerator', 'src')
        ]
        self.execution_history = []
        self.max_history = 100
    
    def execute_python_file(self, file_path: str, args: List[str] = None, timeout: int = 300) -> Dict:
        """Execute a Python file"""
        try:
            # Validate file path
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.base_dir, file_path)
            
            file_path = os.path.normpath(file_path)
            
            # Security check - ensure file is in allowed directory
            if not self._is_allowed_path(file_path):
                return {
                    'success': False,
                    'error': f'File path not allowed: {file_path}',
                    'allowed_directories': self.allowed_directories
                }
            
            # Check if file exists
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'File not found: {file_path}'
                }
            
            # Execute the file
            cmd = [sys.executable, file_path]
            if args:
                cmd.extend(args)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.path.dirname(file_path) or self.base_dir
            )
            
            execution_result = {
                'success': result.returncode == 0,
                'file': file_path,
                'args': args or [],
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(cmd)
            }
            
            # Add to history
            self._add_to_history(execution_result)
            
            return execution_result
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f'Execution timeout after {timeout} seconds',
                'file': file_path
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'file': file_path
            }
    
    def execute_python_code(self, code: str, timeout: int = 60) -> Dict:
        """Execute Python code string"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            try:
                # Execute the temporary file
                result = subprocess.run(
                    [sys.executable, temp_file],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=self.base_dir
                )
                
                execution_result = {
                    'success': result.returncode == 0,
                    'code_length': len(code),
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
                
                # Add to history
                self._add_to_history(execution_result)
                
                return execution_result
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f'Execution timeout after {timeout} seconds'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def list_available_scripts(self, directory: Optional[str] = None) -> Dict:
        """List available Python scripts"""
        try:
            if directory:
                search_dir = os.path.join(self.base_dir, directory)
            else:
                search_dir = self.base_dir
            
            scripts = []
            
            for allowed_dir in self.allowed_directories:
                if os.path.exists(allowed_dir):
                    for root, dirs, files in os.walk(allowed_dir):
                        # Skip hidden directories
                        dirs[:] = [d for d in dirs if not d.startswith('.')]
                        
                        for file in files:
                            if file.endswith('.py') and not file.startswith('__'):
                                full_path = os.path.join(root, file)
                                rel_path = os.path.relpath(full_path, self.base_dir)
                                scripts.append({
                                    'name': file,
                                    'path': full_path,
                                    'relative_path': rel_path,
                                    'directory': os.path.dirname(rel_path)
                                })
            
            return {
                'success': True,
                'scripts': scripts,
                'count': len(scripts)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def _is_allowed_path(self, file_path: str) -> bool:
        """Check if file path is in allowed directory"""
        file_path = os.path.normpath(file_path)
        
        for allowed_dir in self.allowed_directories:
            allowed_dir = os.path.normpath(allowed_dir)
            try:
                # Check if file is within allowed directory
                common_path = os.path.commonpath([file_path, allowed_dir])
                if common_path == allowed_dir:
                    return True
            except ValueError:
                # Paths don't share a common path
                continue
        
        return False
    
    def _add_to_history(self, execution_result: Dict):
        """Add execution result to history"""
        import datetime
        execution_result['timestamp'] = datetime.datetime.now().isoformat()
        self.execution_history.append(execution_result)
        
        # Keep only last max_history entries
        if len(self.execution_history) > self.max_history:
            self.execution_history = self.execution_history[-self.max_history:]
    
    def get_execution_history(self, limit: int = 50) -> Dict:
        """Get execution history"""
        return {
            'success': True,
            'history': self.execution_history[-limit:] if limit else self.execution_history,
            'total': len(self.execution_history)
        }
    
    def get_script_info(self, file_path: str) -> Dict:
        """Get information about a Python script"""
        try:
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.base_dir, file_path)
            
            file_path = os.path.normpath(file_path)
            
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': 'File not found'
                }
            
            # Read file and extract info
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract docstring
            docstring = None
            if content.startswith('"""') or content.startswith("'''"):
                end_quote = content.find('"""', 3) if content.startswith('"""') else content.find("'''", 3)
                if end_quote > 0:
                    docstring = content[3:end_quote].strip()
            
            # Count lines, functions, classes
            lines = content.split('\n')
            functions = [line for line in lines if line.strip().startswith('def ')]
            classes = [line for line in lines if line.strip().startswith('class ')]
            
            return {
                'success': True,
                'file': file_path,
                'size': len(content),
                'lines': len(lines),
                'functions': len(functions),
                'classes': len(classes),
                'docstring': docstring,
                'functions_list': [f.strip().split('(')[0].replace('def ', '') for f in functions],
                'classes_list': [c.strip().split('(')[0].replace('class ', '').split(':')[0] for c in classes]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }

# Global instance
agent_python_executor = AgentPythonExecutor()

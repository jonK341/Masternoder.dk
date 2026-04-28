"""
Agent Error Handler Integration
Integrates agents with error handlers and log files for analysis and use case generation
"""
import os
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentErrorHandler:
    """Agent integration with error handlers and log files"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.errors_file = os.path.join(self.base_dir, 'logs', 'agent_errors', 'errors.json')
        self.use_cases_file = os.path.join(self.base_dir, 'logs', 'agent_errors', 'use_cases.json')
        self.load_data()
    
    def load_data(self):
        """Load error and use case data"""
        os.makedirs(os.path.dirname(self.errors_file), exist_ok=True)
        
        if os.path.exists(self.errors_file):
            try:
                with open(self.errors_file, 'r') as f:
                    self.errors = json.load(f)
            except:
                self.errors = self._default_errors()
        else:
            self.errors = self._default_errors()
            self.save_errors()
        
        if os.path.exists(self.use_cases_file):
            try:
                with open(self.use_cases_file, 'r') as f:
                    self.use_cases = json.load(f)
            except:
                self.use_cases = self._default_use_cases()
        else:
            self.use_cases = self._default_use_cases()
            self.save_use_cases()
    
    def _default_errors(self) -> Dict:
        """Default errors structure"""
        return {
            'errors': [],
            'error_patterns': {},
            'error_categories': {},
            'error_statistics': {},
            'last_updated': datetime.now().isoformat()
        }
    
    def _default_use_cases(self) -> Dict:
        """Default use cases structure"""
        return {
            'use_cases': [],
            'use_case_templates': {},
            'solution_patterns': {},
            'last_updated': datetime.now().isoformat()
        }
    
    def save_errors(self):
        """Save error data"""
        try:
            self.errors['last_updated'] = datetime.now().isoformat()
            with open(self.errors_file, 'w') as f:
                json.dump(self.errors, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving errors: {e}")
    
    def save_use_cases(self):
        """Save use case data"""
        try:
            self.use_cases['last_updated'] = datetime.now().isoformat()
            with open(self.use_cases_file, 'w') as f:
                json.dump(self.use_cases, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving use cases: {e}")
    
    def capture_error(self, agent_id: str, error_type: str, error_message: str, 
                     context: Dict = None, stack_trace: str = None) -> Dict:
        """Capture an error from agent or system"""
        error_entry = {
            'id': f"error_{len(self.errors['errors']) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'agent_id': agent_id,
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {},
            'stack_trace': stack_trace,
            'timestamp': datetime.now().isoformat(),
            'status': 'new',
            'resolved': False,
            'use_case_id': None
        }
        
        self.errors['errors'].append(error_entry)
        
        # Update statistics
        if error_type not in self.errors['error_statistics']:
            self.errors['error_statistics'][error_type] = {
                'count': 0,
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat()
            }
        self.errors['error_statistics'][error_type]['count'] += 1
        self.errors['error_statistics'][error_type]['last_seen'] = datetime.now().isoformat()
        
        # Categorize error
        category = self._categorize_error(error_type, error_message)
        if category not in self.errors['error_categories']:
            self.errors['error_categories'][category] = []
        self.errors['error_categories'][category].append(error_entry['id'])
        
        # Keep only last 1000 errors
        if len(self.errors['errors']) > 1000:
            self.errors['errors'] = self.errors['errors'][-1000:]
        
        self.save_errors()
        return error_entry
    
    def _categorize_error(self, error_type: str, error_message: str) -> str:
        """Categorize error based on type and message"""
        error_lower = error_message.lower()
        
        if 'import' in error_lower or 'module' in error_lower or 'importerror' in error_type.lower():
            return 'import_error'
        elif 'database' in error_lower or 'sql' in error_lower or 'db' in error_lower:
            return 'database_error'
        elif 'network' in error_lower or 'connection' in error_lower or 'timeout' in error_lower:
            return 'network_error'
        elif 'authentication' in error_lower or 'authorization' in error_lower or 'permission' in error_lower:
            return 'auth_error'
        elif 'validation' in error_lower or 'invalid' in error_lower or 'format' in error_lower:
            return 'validation_error'
        elif 'not found' in error_lower or '404' in error_lower or 'missing' in error_lower:
            return 'not_found_error'
        elif 'server' in error_lower or '500' in error_lower or 'internal' in error_lower:
            return 'server_error'
        else:
            return 'general_error'
    
    def analyze_log_file(self, log_file_path: str, agent_id: str = 'system') -> Dict:
        """Analyze a log file for errors"""
        errors_found = []
        
        try:
            if not os.path.exists(log_file_path):
                return {
                    'success': False,
                    'error': 'Log file not found',
                    'errors_found': []
                }
            
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Look for error patterns
            error_patterns = [
                (r'ERROR', 'ERROR'),
                (r'EXCEPTION', 'EXCEPTION'),
                (r'Traceback', 'TRACEBACK'),
                (r'Exception:', 'EXCEPTION'),
                (r'Error:', 'ERROR'),
                (r'Failed', 'FAILED'),
                (r'Critical', 'CRITICAL')
            ]
            
            for i, line in enumerate(lines):
                for pattern, error_type in error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Extract context (previous and next lines)
                        context_start = max(0, i - 2)
                        context_end = min(len(lines), i + 3)
                        context = '\n'.join(lines[context_start:context_end])
                        
                        error_entry = self.capture_error(
                            agent_id=agent_id,
                            error_type=error_type,
                            error_message=line.strip(),
                            context={'line_number': i + 1, 'context': context, 'log_file': log_file_path}
                        )
                        errors_found.append(error_entry)
                        break
            
            return {
                'success': True,
                'log_file': log_file_path,
                'errors_found': errors_found,
                'count': len(errors_found)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'errors_found': []
            }
    
    def analyze_log_directory(self, log_dir: str, agent_id: str = 'system') -> Dict:
        """Analyze all log files in a directory"""
        all_errors = []
        files_analyzed = []
        
        try:
            if not os.path.exists(log_dir):
                return {
                    'success': False,
                    'error': 'Log directory not found',
                    'errors_found': []
                }
            
            log_files = []
            for root, dirs, files in os.walk(log_dir):
                for file in files:
                    if file.endswith('.log') or file.endswith('.txt'):
                        log_files.append(os.path.join(root, file))
            
            for log_file in log_files:
                result = self.analyze_log_file(log_file, agent_id)
                if result.get('success'):
                    all_errors.extend(result.get('errors_found', []))
                    files_analyzed.append(log_file)
            
            return {
                'success': True,
                'log_directory': log_dir,
                'files_analyzed': files_analyzed,
                'errors_found': all_errors,
                'count': len(all_errors)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'errors_found': []
            }
    
    def generate_use_case_from_error(self, error_id: str, agent_id: str = 'ai_agent') -> Dict:
        """Generate an AI-powered use case to solve an error"""
        error = next((e for e in self.errors['errors'] if e['id'] == error_id), None)
        if not error:
            return {
                'success': False,
                'error': 'Error not found'
            }
        
        # Use AI intelligence to generate use case
        use_case = self._create_ai_use_case(error, agent_id)
        
        # Store use case
        self.use_cases['use_cases'].append(use_case)
        
        # Link error to use case
        error['use_case_id'] = use_case['id']
        error['status'] = 'use_case_generated'
        
        # Keep only last 500 use cases
        if len(self.use_cases['use_cases']) > 500:
            self.use_cases['use_cases'] = self.use_cases['use_cases'][-500:]
        
        self.save_errors()
        self.save_use_cases()
        
        return {
            'success': True,
            'error': error,
            'use_case': use_case
        }
    
    def _create_ai_use_case(self, error: Dict, agent_id: str) -> Dict:
        """Create an AI-powered use case using intelligence system"""
        try:
            from backend.services.agent_ai_intelligence import agent_ai_intelligence
            
            # Analyze error context
            error_type = error.get('error_type', 'UNKNOWN')
            error_message = error.get('error_message', '')
            context = error.get('context', {})
            
            # Use AI to understand the problem
            understanding = agent_ai_intelligence.understand_context(
                agent_id,
                {
                    'error_type': error_type,
                    'error_message': error_message,
                    'context': context
                }
            )
            
            # Generate solution strategy
            goal = f"Fix {error_type} error: {error_message[:100]}"
            strategy = agent_ai_intelligence.develop_strategy(agent_id, goal, {
                'error_type': error_type,
                'context': context
            })
            
            # Generate use case
            use_case_id = f"usecase_{len(self.use_cases['use_cases']) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            use_case = {
                'id': use_case_id,
                'error_id': error['id'],
                'agent_id': agent_id,
                'title': f"Fix {error_type} Error",
                'description': f"Use case to resolve error: {error_message[:200]}",
                'problem': {
                    'error_type': error_type,
                    'error_message': error_message,
                    'context': context
                },
                'solution': {
                    'strategy': strategy,
                    'steps': self._generate_solution_steps(error_type, error_message, context),
                    'prevention': self._generate_prevention_steps(error_type)
                },
                'priority': self._calculate_priority(error),
                'status': 'draft',
                'created_at': datetime.now().isoformat(),
                'resolved': False
            }
            
            return use_case
        except Exception as e:
            # Fallback use case if AI intelligence fails
            return self._create_fallback_use_case(error, agent_id)
    
    def _generate_solution_steps(self, error_type: str, error_message: str, context: Dict) -> List[Dict]:
        """Generate solution steps based on error"""
        steps = []
        
        error_lower = error_message.lower()
        category = self._categorize_error(error_type, error_message)
        
        if category == 'import_error':
            steps = [
                {'step': 1, 'action': 'Check if module is installed', 'description': 'Verify required packages'},
                {'step': 2, 'action': 'Check import paths', 'description': 'Verify correct import statements'},
                {'step': 3, 'action': 'Install missing dependencies', 'description': 'Install required packages'},
                {'step': 4, 'action': 'Verify Python path', 'description': 'Check sys.path configuration'}
            ]
        elif category == 'database_error':
            steps = [
                {'step': 1, 'action': 'Check database connection', 'description': 'Verify database is accessible'},
                {'step': 2, 'action': 'Check SQL syntax', 'description': 'Verify query syntax'},
                {'step': 3, 'action': 'Check database schema', 'description': 'Verify table/column existence'},
                {'step': 4, 'action': 'Check permissions', 'description': 'Verify database user permissions'}
            ]
        elif category == 'network_error':
            steps = [
                {'step': 1, 'action': 'Check network connectivity', 'description': 'Verify network connection'},
                {'step': 2, 'action': 'Check endpoint availability', 'description': 'Verify target endpoint'},
                {'step': 3, 'action': 'Check firewall settings', 'description': 'Verify firewall rules'},
                {'step': 4, 'action': 'Check timeout settings', 'description': 'Adjust timeout values'}
            ]
        else:
            steps = [
                {'step': 1, 'action': 'Analyze error message', 'description': 'Understand the error'},
                {'step': 2, 'action': 'Check context and logs', 'description': 'Review related information'},
                {'step': 3, 'action': 'Research solution', 'description': 'Find similar solved issues'},
                {'step': 4, 'action': 'Implement fix', 'description': 'Apply solution'},
                {'step': 5, 'action': 'Test and verify', 'description': 'Verify fix works'}
            ]
        
        return steps
    
    def _generate_prevention_steps(self, error_type: str) -> List[str]:
        """Generate prevention steps"""
        return [
            f'Add error handling for {error_type}',
            'Add input validation',
            'Add logging and monitoring',
            'Add automated tests',
            'Document error scenarios'
        ]
    
    def _calculate_priority(self, error: Dict) -> str:
        """Calculate priority based on error"""
        error_type = error.get('error_type', '')
        error_lower = error_type.lower()
        
        if 'critical' in error_lower or 'fatal' in error_lower:
            return 'high'
        elif 'error' in error_lower:
            return 'medium'
        else:
            return 'low'
    
    def _create_fallback_use_case(self, error: Dict, agent_id: str) -> Dict:
        """Create fallback use case if AI fails"""
        use_case_id = f"usecase_{len(self.use_cases['use_cases']) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return {
            'id': use_case_id,
            'error_id': error['id'],
            'agent_id': agent_id,
            'title': f"Fix {error.get('error_type', 'UNKNOWN')} Error",
            'description': f"Use case to resolve error: {error.get('error_message', 'Unknown error')[:200]}",
            'problem': {
                'error_type': error.get('error_type'),
                'error_message': error.get('error_message'),
                'context': error.get('context', {})
            },
            'solution': {
                'steps': self._generate_solution_steps(
                    error.get('error_type', ''),
                    error.get('error_message', ''),
                    error.get('context', {})
                ),
                'prevention': self._generate_prevention_steps(error.get('error_type', ''))
            },
            'priority': self._calculate_priority(error),
            'status': 'draft',
            'created_at': datetime.now().isoformat(),
            'resolved': False
        }
    
    def get_errors(self, agent_id: Optional[str] = None, status: Optional[str] = None, 
                   category: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get errors with filters"""
        errors = self.errors['errors']
        
        if agent_id:
            errors = [e for e in errors if e.get('agent_id') == agent_id]
        
        if status:
            errors = [e for e in errors if e.get('status') == status]
        
        if category:
            error_ids = self.errors['error_categories'].get(category, [])
            errors = [e for e in errors if e['id'] in error_ids]
        
        return errors[-limit:] if len(errors) > limit else errors
    
    def get_use_cases(self, error_id: Optional[str] = None, agent_id: Optional[str] = None,
                      status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get use cases with filters"""
        use_cases = self.use_cases['use_cases']
        
        if error_id:
            use_cases = [uc for uc in use_cases if uc.get('error_id') == error_id]
        
        if agent_id:
            use_cases = [uc for uc in use_cases if uc.get('agent_id') == agent_id]
        
        if status:
            use_cases = [uc for uc in use_cases if uc.get('status') == status]
        
        return use_cases[-limit:] if len(use_cases) > limit else use_cases
    
    def get_error_statistics(self) -> Dict:
        """Get error statistics"""
        return {
            'total_errors': len(self.errors['errors']),
            'unresolved_errors': len([e for e in self.errors['errors'] if not e.get('resolved', False)]),
            'error_statistics': self.errors['error_statistics'],
            'error_categories': {cat: len(ids) for cat, ids in self.errors['error_categories'].items()},
            'total_use_cases': len(self.use_cases['use_cases']),
            'unresolved_use_cases': len([uc for uc in self.use_cases['use_cases'] if not uc.get('resolved', False)])
        }
    
    def resolve_error(self, error_id: str, resolution_notes: str = '') -> Dict:
        """Mark error as resolved"""
        error = next((e for e in self.errors['errors'] if e['id'] == error_id), None)
        if not error:
            return {'success': False, 'error': 'Error not found'}
        
        error['resolved'] = True
        error['status'] = 'resolved'
        error['resolution_notes'] = resolution_notes
        error['resolved_at'] = datetime.now().isoformat()
        
        # Resolve linked use case
        if error.get('use_case_id'):
            use_case = next((uc for uc in self.use_cases['use_cases'] if uc['id'] == error['use_case_id']), None)
            if use_case:
                use_case['resolved'] = True
                use_case['status'] = 'resolved'
                use_case['resolved_at'] = datetime.now().isoformat()
        
        self.save_errors()
        self.save_use_cases()
        
        return {'success': True, 'error': error}

# Global instance
agent_error_handler = AgentErrorHandler()

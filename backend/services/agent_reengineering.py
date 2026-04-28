"""
Agent Reengineering Service
Learns from tasks and creates autofix handlers for missing handlers that need migration
"""
import os
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AgentReengineering:
    """Agent reengineering system that learns from tasks and creates autofix handlers"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.learning_file = os.path.join(self.base_dir, 'logs', 'agent_reengineering', 'learning.json')
        self.handlers_file = os.path.join(self.base_dir, 'logs', 'agent_reengineering', 'autofix_handlers.json')
        self.load_data()
    
    def load_data(self):
        """Load learning and handler data"""
        os.makedirs(os.path.dirname(self.learning_file), exist_ok=True)
        
        # Load learning data
        if os.path.exists(self.learning_file):
            try:
                with open(self.learning_file, 'r') as f:
                    self.learning = json.load(f)
            except:
                self.learning = self._default_learning()
        else:
            self.learning = self._default_learning()
        
        # Load handlers
        if os.path.exists(self.handlers_file):
            try:
                with open(self.handlers_file, 'r') as f:
                    self.handlers = json.load(f)
            except:
                self.handlers = {}
        else:
            self.handlers = {}
        
        self.save_data()
    
    def _default_learning(self) -> Dict:
        """Default learning data structure"""
        return {
            'task_patterns': {},
            'error_patterns': {},
            'fix_patterns': {},
            'handler_templates': {},
            'success_rate': {},
            'last_updated': datetime.now().isoformat()
        }
    
    def save_data(self):
        """Save learning and handler data"""
        try:
            self.learning['last_updated'] = datetime.now().isoformat()
            with open(self.learning_file, 'w') as f:
                json.dump(self.learning, f, indent=2, default=str)
            with open(self.handlers_file, 'w') as f:
                json.dump(self.handlers, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving reengineering data: {e}")
    
    def learn_from_task(self, task_data: Dict, result_data: Dict) -> Dict:
        """Learn from a completed task"""
        task_type = task_data.get('task_type', 'unknown')
        action = task_data.get('action', '')
        success = result_data.get('success', False)
        
        # Extract patterns
        error_message = result_data.get('error', '')
        fix_applied = result_data.get('fix_applied', '')
        
        # Update task patterns
        if task_type not in self.learning['task_patterns']:
            self.learning['task_patterns'][task_type] = {
                'count': 0,
                'success_count': 0,
                'common_errors': [],
                'common_fixes': []
            }
        
        pattern = self.learning['task_patterns'][task_type]
        pattern['count'] += 1
        if success:
            pattern['success_count'] += 1
        
        # Learn error patterns
        if error_message:
            error_key = self._extract_error_pattern(error_message)
            if error_key not in self.learning['error_patterns']:
                self.learning['error_patterns'][error_key] = {
                    'count': 0,
                    'contexts': [],
                    'fixes': []
                }
            self.learning['error_patterns'][error_key]['count'] += 1
            self.learning['error_patterns'][error_key]['contexts'].append({
                'task_type': task_type,
                'action': action,
                'timestamp': datetime.now().isoformat()
            })
            if len(self.learning['error_patterns'][error_key]['contexts']) > 100:
                self.learning['error_patterns'][error_key]['contexts'] = \
                    self.learning['error_patterns'][error_key]['contexts'][-100:]
        
        # Learn fix patterns
        if fix_applied and success:
            fix_key = self._extract_fix_pattern(fix_applied)
            if fix_key not in self.learning['fix_patterns']:
                self.learning['fix_patterns'][fix_key] = {
                    'count': 0,
                    'success_count': 0,
                    'contexts': []
                }
            self.learning['fix_patterns'][fix_key]['count'] += 1
            self.learning['fix_patterns'][fix_key]['success_count'] += 1
            self.learning['fix_patterns'][fix_key]['contexts'].append({
                'task_type': task_type,
                'error': error_key if error_message else None,
                'timestamp': datetime.now().isoformat()
            })
            if len(self.learning['fix_patterns'][fix_key]['contexts']) > 100:
                self.learning['fix_patterns'][fix_key]['contexts'] = \
                    self.learning['fix_patterns'][fix_key]['contexts'][-100:]
        
        # Update success rate
        pattern['success_rate'] = pattern['success_count'] / pattern['count'] if pattern['count'] > 0 else 0.0
        self.learning['success_rate'][task_type] = pattern['success_rate']
        
        self.save_data()
        
        return {
            'learned': True,
            'patterns_updated': True,
            'task_type': task_type
        }
    
    def _extract_error_pattern(self, error_message: str) -> str:
        """Extract error pattern from error message"""
        # Remove specific details, keep structure
        pattern = error_message.lower()
        # Remove file paths
        pattern = re.sub(r'[a-z]:\\[^\s]+|/[^\s]+', '[PATH]', pattern)
        # Remove line numbers
        pattern = re.sub(r'line\s+\d+', 'line [N]', pattern)
        # Remove specific values
        pattern = re.sub(r'\d+', '[N]', pattern)
        return pattern[:200]  # Limit length
    
    def _extract_fix_pattern(self, fix_applied: str) -> str:
        """Extract fix pattern from fix description"""
        # Normalize fix description
        pattern = fix_applied.lower()
        # Remove specific values
        pattern = re.sub(r'\d+', '[N]', pattern)
        # Remove file paths
        pattern = re.sub(r'[a-z]:\\[^\s]+|/[^\s]+', '[PATH]', pattern)
        return pattern[:200]
    
    def create_autofix_handler(self, handler_type: str, context: Dict) -> Dict:
        """Create an autofix handler based on learned patterns"""
        handler_id = f"autofix_{handler_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Get relevant patterns
        error_patterns = self._get_relevant_error_patterns(context)
        fix_patterns = self._get_relevant_fix_patterns(context)
        
        # Generate handler code
        handler_code = self._generate_handler_code(handler_type, error_patterns, fix_patterns, context)
        
        handler = {
            'handler_id': handler_id,
            'handler_type': handler_type,
            'context': context,
            'code': handler_code,
            'patterns_used': {
                'error_patterns': error_patterns,
                'fix_patterns': fix_patterns
            },
            'created_at': datetime.now().isoformat(),
            'status': 'active',
            'success_count': 0,
            'failure_count': 0
        }
        
        self.handlers[handler_id] = handler
        self.save_data()
        
        return handler
    
    def _get_relevant_error_patterns(self, context: Dict) -> List[Dict]:
        """Get relevant error patterns for context"""
        task_type = context.get('task_type', '')
        relevant = []
        
        for error_key, error_data in self.learning['error_patterns'].items():
            # Check if error pattern is relevant to this context
            contexts = error_data.get('contexts', [])
            for ctx in contexts:
                if ctx.get('task_type') == task_type:
                    relevant.append({
                        'pattern': error_key,
                        'count': error_data['count'],
                        'context': ctx
                    })
                    break
        
        # Sort by count (most common first)
        relevant.sort(key=lambda x: x['count'], reverse=True)
        return relevant[:5]  # Top 5
    
    def _get_relevant_fix_patterns(self, context: Dict) -> List[Dict]:
        """Get relevant fix patterns for context"""
        task_type = context.get('task_type', '')
        relevant = []
        
        for fix_key, fix_data in self.learning['fix_patterns'].items():
            # Check if fix pattern is relevant to this context
            contexts = fix_data.get('contexts', [])
            for ctx in contexts:
                if ctx.get('task_type') == task_type:
                    success_rate = fix_data['success_count'] / fix_data['count'] if fix_data['count'] > 0 else 0.0
                    relevant.append({
                        'pattern': fix_key,
                        'count': fix_data['count'],
                        'success_rate': success_rate,
                        'context': ctx
                    })
                    break
        
        # Sort by success rate and count
        relevant.sort(key=lambda x: (x['success_rate'], x['count']), reverse=True)
        return relevant[:5]  # Top 5
    
    def _generate_handler_code(self, handler_type: str, error_patterns: List[Dict], 
                              fix_patterns: List[Dict], context: Dict) -> str:
        """Generate handler code based on patterns"""
        code = f"""# Auto-generated handler for {handler_type}
# Created: {datetime.now().isoformat()}
# Context: {json.dumps(context, indent=2)}

def autofix_handler(error_message, task_context):
    \"\"\"
    Auto-generated fix handler based on learned patterns
    \"\"\"
    error_lower = error_message.lower()
    
    # Error pattern matching
"""
        
        # Add error pattern checks
        for i, error_pattern in enumerate(error_patterns[:3]):  # Top 3 error patterns
            pattern = error_pattern['pattern']
            code += f"""
    # Pattern {i+1}: {pattern[:50]}...
    if '{pattern[:30]}' in error_lower:
"""
            # Add corresponding fix
            if fix_patterns:
                fix_pattern = fix_patterns[0]['pattern']
                code += f"""        # Apply fix: {fix_pattern[:50]}...
        return apply_fix_pattern_{i+1}(error_message, task_context)
"""
        
        code += """
    # Default: no fix found
    return {
        'success': False,
        'message': 'No matching fix pattern found',
        'error': error_message
    }

"""
        
        # Add fix pattern functions
        for i, fix_pattern in enumerate(fix_patterns[:3]):  # Top 3 fix patterns
            code += f"""
def apply_fix_pattern_{i+1}(error_message, task_context):
    \"\"\"
    Apply fix pattern {i+1}
    Pattern: {fix_pattern['pattern'][:100]}...
    \"\"\"
    # TODO: Implement fix based on learned pattern
    # This should be customized based on actual fix patterns learned
    return {{
        'success': True,
        'message': 'Fix applied (pattern {i+1})',
        'fix_type': 'pattern_{i+1}'
    }}
"""
        
        return code
    
    def get_missing_handlers(self) -> List[Dict]:
        """Get list of missing handlers that need migration"""
        missing = []
        
        # Analyze error patterns that don't have handlers
        for error_key, error_data in self.learning['error_patterns'].items():
            # Check if handler exists for this error pattern
            has_handler = False
            for handler_id, handler in self.handlers.items():
                patterns_used = handler.get('patterns_used', {}).get('error_patterns', [])
                for pattern in patterns_used:
                    if pattern.get('pattern') == error_key:
                        has_handler = True
                        break
                if has_handler:
                    break
            
            if not has_handler and error_data['count'] >= 3:  # At least 3 occurrences
                missing.append({
                    'error_pattern': error_key,
                    'occurrences': error_data['count'],
                    'contexts': error_data.get('contexts', [])[:5],
                    'priority': 'high' if error_data['count'] >= 10 else 'medium'
                })
        
        # Sort by priority and occurrences
        missing.sort(key=lambda x: (x['priority'] == 'high', x['occurrences']), reverse=True)
        
        return missing
    
    def auto_create_missing_handlers(self) -> List[Dict]:
        """Automatically create handlers for missing handlers"""
        missing = self.get_missing_handlers()
        created = []
        
        for missing_handler in missing[:5]:  # Create top 5 missing handlers
            error_pattern = missing_handler['error_pattern']
            context = missing_handler['contexts'][0] if missing_handler['contexts'] else {}
            
            handler = self.create_autofix_handler(
                handler_type=f"missing_{error_pattern[:30]}",
                context={
                    'task_type': context.get('task_type', 'unknown'),
                    'error_pattern': error_pattern,
                    'auto_created': True
                }
            )
            created.append(handler)
        
        return created


# Global instance
agent_reengineering = AgentReengineering()

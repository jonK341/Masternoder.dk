"""
Advanced AI-Powered Debugger Engine
Intelligent debugging with pattern recognition, predictive analysis, and auto-fix
"""
import os
import json
import re
import ast
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class AdvancedAIDebuggerEngine:
    """Advanced AI-powered debugging engine with intelligent analysis"""
    
    def __init__(self):
        self.error_patterns = self._load_error_patterns()
        self.fix_history = []
        self.performance_metrics = defaultdict(list)
        self.code_analysis_cache = {}
        
        # Initialize AI models if available
        self.ai_available = False
        if OPENAI_AVAILABLE:
            try:
                openai.api_key = os.getenv('OPENAI_API_KEY', '')
                self.ai_available = bool(openai.api_key)
            except:
                pass
        
        # Initialize transformers for code analysis
        self.code_analyzer = None
        if TRANSFORMERS_AVAILABLE:
            try:
                self.code_analyzer = pipeline("text-classification", 
                    model="microsoft/DialoGPT-medium", 
                    device=-1)  # Use CPU
            except:
                pass
    
    def _load_error_patterns(self) -> Dict:
        """Load intelligent error patterns with context"""
        return {
            'authentication_failed': {
                'patterns': [
                    r'authentication.*failed',
                    r'401.*unauthorized',
                    r'invalid.*credentials',
                    r'permission.*denied'
                ],
                'severity': 'high',
                'category': 'security',
                'suggestions': [
                    'Check API keys and credentials',
                    'Verify user permissions',
                    'Review authentication middleware',
                    'Check token expiration'
                ],
                'auto_fixable': False
            },
            'database_error': {
                'patterns': [
                    r'database.*error',
                    r'sql.*error',
                    r'connection.*refused',
                    r'table.*doesn\'t exist',
                    r'column.*doesn\'t exist'
                ],
                'severity': 'high',
                'category': 'database',
                'suggestions': [
                    'Check database connection',
                    'Verify table schema',
                    'Run database migrations',
                    'Check database permissions'
                ],
                'auto_fixable': True
            },
            'import_error': {
                'patterns': [
                    r'import.*error',
                    r'module.*not found',
                    r'cannot import',
                    r'no module named'
                ],
                'severity': 'medium',
                'category': 'dependencies',
                'suggestions': [
                    'Install missing packages',
                    'Check virtual environment',
                    'Verify Python path',
                    'Update requirements.txt'
                ],
                'auto_fixable': True
            },
            'route_not_found': {
                'patterns': [
                    r'404.*not found',
                    r'route.*not found',
                    r'endpoint.*doesn\'t exist'
                ],
                'severity': 'medium',
                'category': 'routing',
                'suggestions': [
                    'Check route registration',
                    'Verify URL patterns',
                    'Check blueprint registration',
                    'Review middleware configuration'
                ],
                'auto_fixable': True
            },
            'performance_issue': {
                'patterns': [
                    r'slow.*query',
                    r'timeout',
                    r'performance.*degraded',
                    r'high.*latency'
                ],
                'severity': 'medium',
                'category': 'performance',
                'suggestions': [
                    'Optimize database queries',
                    'Add caching',
                    'Review N+1 queries',
                    'Check resource usage'
                ],
                'auto_fixable': False
            },
            'memory_error': {
                'patterns': [
                    r'memory.*error',
                    r'out of memory',
                    r'memory.*leak'
                ],
                'severity': 'high',
                'category': 'resource',
                'suggestions': [
                    'Check for memory leaks',
                    'Optimize data structures',
                    'Add garbage collection',
                    'Increase memory limits'
                ],
                'auto_fixable': False
            }
        }
    
    def analyze_error_with_ai(self, error_message: str, context: Dict = None) -> Dict:
        """Analyze error with AI-powered insights"""
        context = context or {}
        
        # Pattern matching
        error_type = self._identify_error_type(error_message)
        pattern_info = self.error_patterns.get(error_type, {})
        
        # Code analysis
        code_issues = []
        if context.get('code'):
            code_issues = self._analyze_code(context['code'])
        
        # Performance analysis
        performance_issues = []
        if context.get('performance_metrics'):
            performance_issues = self._analyze_performance(context['performance_metrics'])
        
        # AI-powered insights
        ai_insights = []
        if self.ai_available:
            ai_insights = self._generate_ai_insights(error_message, context)
        
        # Predictive analysis
        predictions = self._predict_future_errors(error_message, context)
        
        # Auto-fix suggestions
        auto_fix = None
        if pattern_info.get('auto_fixable'):
            auto_fix = self._generate_auto_fix(error_message, context)
        
        return {
            'error_type': error_type,
            'severity': pattern_info.get('severity', 'unknown'),
            'category': pattern_info.get('category', 'unknown'),
            'suggestions': pattern_info.get('suggestions', []),
            'code_issues': code_issues,
            'performance_issues': performance_issues,
            'ai_insights': ai_insights,
            'predictions': predictions,
            'auto_fix': auto_fix,
            'confidence': self._calculate_confidence(error_message, error_type),
            'timestamp': datetime.now().isoformat()
        }
    
    def _identify_error_type(self, error_message: str) -> str:
        """Identify error type using pattern matching"""
        error_lower = error_message.lower()
        
        for error_type, pattern_info in self.error_patterns.items():
            for pattern in pattern_info['patterns']:
                if re.search(pattern, error_lower, re.IGNORECASE):
                    return error_type
        
        return 'unknown'
    
    def _analyze_code(self, code: str) -> List[Dict]:
        """Analyze code for potential issues"""
        issues = []
        
        try:
            tree = ast.parse(code)
            
            # Check for common issues
            for node in ast.walk(tree):
                # Check for bare except
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    issues.append({
                        'type': 'bare_except',
                        'severity': 'medium',
                        'line': node.lineno,
                        'message': 'Bare except clause catches all exceptions',
                        'suggestion': 'Specify exception types'
                    })
                
                # Check for unused imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.asname:
                            # Check if used
                            pass
            
            # Check code complexity
            complexity = self._calculate_complexity(tree)
            if complexity > 10:
                issues.append({
                    'type': 'high_complexity',
                    'severity': 'low',
                    'message': f'Function complexity is {complexity} (recommended: <10)',
                    'suggestion': 'Consider refactoring into smaller functions'
                })
            
        except SyntaxError as e:
            issues.append({
                'type': 'syntax_error',
                'severity': 'high',
                'message': f'Syntax error: {str(e)}',
                'line': e.lineno
            })
        except Exception as e:
            issues.append({
                'type': 'analysis_error',
                'severity': 'low',
                'message': f'Could not analyze code: {str(e)}'
            })
        
        return issues
    
    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                complexity += 1
            if isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        
        return complexity
    
    def _analyze_performance(self, metrics: Dict) -> List[Dict]:
        """Analyze performance metrics"""
        issues = []
        
        # Response time analysis
        if 'response_time' in metrics:
            response_time = metrics['response_time']
            if response_time > 1000:  # > 1 second
                issues.append({
                    'type': 'slow_response',
                    'severity': 'medium',
                    'message': f'Response time is {response_time}ms (recommended: <500ms)',
                    'suggestion': 'Optimize database queries or add caching'
                })
        
        # Memory usage
        if 'memory_usage' in metrics:
            memory = metrics['memory_usage']
            if memory > 500 * 1024 * 1024:  # > 500MB
                issues.append({
                    'type': 'high_memory',
                    'severity': 'medium',
                    'message': f'Memory usage is {memory / 1024 / 1024:.2f}MB',
                    'suggestion': 'Check for memory leaks or optimize data structures'
                })
        
        # Database queries
        if 'db_queries' in metrics:
            queries = metrics['db_queries']
            if queries > 20:
                issues.append({
                    'type': 'too_many_queries',
                    'severity': 'medium',
                    'message': f'{queries} database queries (recommended: <10)',
                    'suggestion': 'Check for N+1 query problems or add eager loading'
                })
        
        return issues
    
    def _generate_ai_insights(self, error_message: str, context: Dict) -> List[str]:
        """Generate AI-powered insights using OpenAI"""
        if not self.ai_available:
            return []
        
        try:
            prompt = f"""Analyze this error and provide intelligent debugging insights:

Error: {error_message}

Context: {json.dumps(context, indent=2)}

Provide 3-5 specific, actionable insights to help debug this issue. Focus on:
1. Root cause analysis
2. Common solutions
3. Prevention strategies
4. Best practices

Format as a JSON array of strings."""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert debugging assistant. Provide concise, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            insights_text = response.choices[0].message.content
            # Try to parse as JSON, fallback to splitting by lines
            try:
                insights = json.loads(insights_text)
            except:
                insights = [line.strip() for line in insights_text.split('\n') if line.strip()]
            
            return insights[:5]  # Limit to 5 insights
            
        except Exception as e:
            logging.warning(f"AI insight generation failed: {e}")
            return []
    
    def _predict_future_errors(self, error_message: str, context: Dict) -> List[Dict]:
        """Predict potential future errors based on current error"""
        predictions = []
        
        # Analyze error patterns in history
        error_type = self._identify_error_type(error_message)
        
        # Check if this error type has occurred frequently
        if error_type in self.fix_history:
            recent_occurrences = [h for h in self.fix_history[error_type] 
                                 if datetime.fromisoformat(h['timestamp']) > datetime.now() - timedelta(hours=24)]
            
            if len(recent_occurrences) > 5:
                predictions.append({
                    'type': 'recurring_error',
                    'message': f'This error has occurred {len(recent_occurrences)} times in the last 24 hours',
                    'severity': 'high',
                    'suggestion': 'This appears to be a recurring issue. Consider implementing a permanent fix.'
                })
        
        # Predict related errors
        if error_type == 'database_error':
            predictions.append({
                'type': 'related_error',
                'message': 'Database errors often lead to authentication failures',
                'severity': 'medium',
                'suggestion': 'Monitor authentication endpoints after fixing database issues'
            })
        
        return predictions
    
    def _generate_auto_fix(self, error_message: str, context: Dict) -> Optional[Dict]:
        """Generate automatic fix for the error"""
        error_type = self._identify_error_type(error_message)
        
        fixes = {
            'import_error': self._fix_import_error,
            'database_error': self._fix_database_error,
            'route_not_found': self._fix_route_error
        }
        
        fix_func = fixes.get(error_type)
        if fix_func:
            return fix_func(error_message, context)
        
        return None
    
    def _fix_import_error(self, error_message: str, context: Dict) -> Dict:
        """Auto-fix import errors"""
        # Extract module name from error
        match = re.search(r"no module named ['\"]([^'\"]+)['\"]", error_message, re.IGNORECASE)
        if match:
            module_name = match.group(1)
            return {
                'type': 'install_package',
                'command': f'pip install {module_name}',
                'description': f'Install missing package: {module_name}',
                'auto_executable': True
            }
        return None
    
    def _fix_database_error(self, error_message: str, context: Dict) -> Dict:
        """Auto-fix database errors"""
        if 'table' in error_message.lower() and "doesn't exist" in error_message.lower():
            return {
                'type': 'run_migration',
                'command': 'flask db upgrade',
                'description': 'Run database migrations to create missing tables',
                'auto_executable': True
            }
        return None
    
    def _fix_route_error(self, error_message: str, context: Dict) -> Dict:
        """Auto-fix route errors"""
        return {
            'type': 'check_blueprint',
            'description': 'Verify blueprint is registered in app.py',
            'steps': [
                'Check if blueprint is imported',
                'Verify blueprint registration',
                'Check URL prefix configuration'
            ],
            'auto_executable': False
        }
    
    def _calculate_confidence(self, error_message: str, error_type: str) -> float:
        """Calculate confidence score for error analysis"""
        if error_type == 'unknown':
            return 0.3
        
        # Check pattern match quality
        pattern_info = self.error_patterns.get(error_type, {})
        matches = sum(1 for pattern in pattern_info.get('patterns', [])
                     if re.search(pattern, error_message, re.IGNORECASE))
        
        if matches > 0:
            return min(0.9, 0.5 + (matches * 0.1))
        
        return 0.5
    
    def analyze_codebase(self, codebase_path: str) -> Dict:
        """Analyze entire codebase for issues"""
        issues = []
        metrics = {
            'total_files': 0,
            'total_lines': 0,
            'complexity_score': 0,
            'test_coverage': 0
        }
        
        for root, dirs, files in os.walk(codebase_path):
            # Skip virtual environments and caches
            dirs[:] = [d for d in dirs if d not in ['.venv', '__pycache__', '.git']]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    metrics['total_files'] += 1
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            code = f.read()
                            metrics['total_lines'] += len(code.splitlines())
                            
                            file_issues = self._analyze_code(code)
                            for issue in file_issues:
                                issue['file'] = file_path
                                issues.append(issue)
                    except Exception as e:
                        issues.append({
                            'type': 'file_read_error',
                            'file': file_path,
                            'message': str(e),
                            'severity': 'low'
                        })
        
        return {
            'issues': issues,
            'metrics': metrics,
            'summary': {
                'total_issues': len(issues),
                'high_severity': len([i for i in issues if i.get('severity') == 'high']),
                'medium_severity': len([i for i in issues if i.get('severity') == 'medium']),
                'low_severity': len([i for i in issues if i.get('severity') == 'low'])
            }
        }
    
    def optimize_performance(self, endpoint: str, metrics: Dict) -> List[Dict]:
        """Provide performance optimization recommendations"""
        recommendations = []
        
        # Database optimization
        if metrics.get('db_queries', 0) > 10:
            recommendations.append({
                'type': 'database',
                'priority': 'high',
                'action': 'Add eager loading',
                'description': f'Endpoint has {metrics["db_queries"]} queries. Use SQLAlchemy eager loading.',
                'impact': 'high',
                'effort': 'medium'
            })
        
        # Caching
        if metrics.get('response_time', 0) > 500:
            recommendations.append({
                'type': 'caching',
                'priority': 'medium',
                'action': 'Add response caching',
                'description': f'Response time is {metrics["response_time"]}ms. Cache responses.',
                'impact': 'high',
                'effort': 'low'
            })
        
        # Memory optimization
        if metrics.get('memory_usage', 0) > 100 * 1024 * 1024:  # > 100MB
            recommendations.append({
                'type': 'memory',
                'priority': 'medium',
                'action': 'Optimize data structures',
                'description': 'High memory usage detected. Review data structures.',
                'impact': 'medium',
                'effort': 'high'
            })
        
        return recommendations


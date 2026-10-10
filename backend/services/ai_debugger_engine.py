"""
AI-Powered Debugger Engine
Intelligent error analysis, pattern detection, and automated fixes
"""
import re
import json
import traceback
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict

class AIDebuggerEngine:
    """AI-powered debugging engine with intelligent analysis"""
    
    def __init__(self):
        self.error_patterns = self._load_error_patterns()
        self.fix_suggestions = self._load_fix_suggestions()
        self.performance_patterns = self._load_performance_patterns()
        self.security_patterns = self._load_security_patterns()
        
    def _load_error_patterns(self) -> Dict[str, Dict]:
        """Load known error patterns for intelligent detection"""
        return {
            '404_not_found': {
                'patterns': [
                    r'404.*not found',
                    r'endpoint.*not found',
                    r'route.*not found',
                    r'404.*error'
                ],
                'severity': 'high',
                'category': 'routing',
                'confidence': 0.9
            },
            '500_internal_error': {
                'patterns': [
                    r'500.*internal',
                    r'internal server error',
                    r'traceback',
                    r'exception.*occurred'
                ],
                'severity': 'critical',
                'category': 'server',
                'confidence': 0.95
            },
            'authentication_failed': {
                'patterns': [
                    r'authentication.*failed',
                    r'unauthorized',
                    r'401.*unauthorized',
                    r'invalid.*credentials'
                ],
                'severity': 'high',
                'category': 'security',
                'confidence': 0.85
            },
            'database_error': {
                'patterns': [
                    r'database.*error',
                    r'sql.*error',
                    r'connection.*refused',
                    r'table.*not found',
                    r'column.*not found'
                ],
                'severity': 'critical',
                'category': 'database',
                'confidence': 0.9
            },
            'timeout_error': {
                'patterns': [
                    r'timeout',
                    r'request.*timeout',
                    r'connection.*timeout',
                    r'504.*gateway'
                ],
                'severity': 'medium',
                'category': 'performance',
                'confidence': 0.8
            },
            'method_not_allowed': {
                'patterns': [
                    r'405.*method',
                    r'method.*not allowed',
                    r'invalid.*method'
                ],
                'severity': 'medium',
                'category': 'routing',
                'confidence': 0.85
            },
            'validation_error': {
                'patterns': [
                    r'validation.*error',
                    r'invalid.*input',
                    r'bad.*request',
                    r'400.*bad request'
                ],
                'severity': 'low',
                'category': 'validation',
                'confidence': 0.75
            }
        }
    
    def _load_fix_suggestions(self) -> Dict[str, List[Dict]]:
        """Load intelligent fix suggestions"""
        return {
            '404_not_found': [
                {
                    'action': 'check_route_registration',
                    'description': 'Verify route is registered in blueprint',
                    'code': 'Check backend/register_blueprints.py',
                    'priority': 1
                },
                {
                    'action': 'check_url_prefix',
                    'description': 'Ensure URL prefix matches middleware',
                    'code': 'Remove /vidgenerator prefix if middleware handles it',
                    'priority': 2
                },
                {
                    'action': 'check_template_path',
                    'description': 'Verify template exists in correct location',
                    'code': 'Check vidgenerator/ or backend/templates/',
                    'priority': 3
                }
            ],
            '500_internal_error': [
                {
                    'action': 'check_logs',
                    'description': 'Review server logs for detailed error',
                    'code': 'journalctl -u python-proxy.service -f',
                    'priority': 1
                },
                {
                    'action': 'check_imports',
                    'description': 'Verify all imports are available',
                    'code': 'Check requirements.txt and installed packages',
                    'priority': 2
                },
                {
                    'action': 'check_database',
                    'description': 'Verify database connection and schema',
                    'code': 'Check database migrations and connections',
                    'priority': 3
                }
            ],
            'authentication_failed': [
                {
                    'action': 'check_credentials',
                    'description': 'Verify username and password',
                    'code': 'Check environment variables or config',
                    'priority': 1
                },
                {
                    'action': 'check_session',
                    'description': 'Verify session management',
                    'code': 'Check Flask session configuration',
                    'priority': 2
                }
            ],
            'database_error': [
                {
                    'action': 'check_connection',
                    'description': 'Verify database connection string',
                    'code': 'Check DATABASE_URL environment variable',
                    'priority': 1
                },
                {
                    'action': 'check_migrations',
                    'description': 'Run database migrations',
                    'code': 'flask db upgrade',
                    'priority': 2
                },
                {
                    'action': 'check_schema',
                    'description': 'Verify table schema matches models',
                    'code': 'Check src/db/models.py',
                    'priority': 3
                }
            ],
            'timeout_error': [
                {
                    'action': 'optimize_query',
                    'description': 'Optimize database queries',
                    'code': 'Add indexes, use eager loading',
                    'priority': 1
                },
                {
                    'action': 'increase_timeout',
                    'description': 'Increase request timeout',
                    'code': 'Configure uWSGI timeout settings',
                    'priority': 2
                },
                {
                    'action': 'add_caching',
                    'description': 'Implement caching for slow operations',
                    'code': 'Use Redis or Flask-Caching',
                    'priority': 3
                }
            ],
            'method_not_allowed': [
                {
                    'action': 'check_route_decorator',
                    'description': 'Verify HTTP method in route decorator',
                    'code': '@route.methods = ["POST"] for POST endpoints',
                    'priority': 1
                },
                {
                    'action': 'check_blueprint',
                    'description': 'Verify blueprint registration',
                    'code': 'Check app.register_blueprint()',
                    'priority': 2
                }
            ]
        }
    
    def _load_performance_patterns(self) -> Dict[str, Any]:
        """Load performance analysis patterns"""
        return {
            'slow_response': {
                'threshold_ms': 1000,
                'suggestions': [
                    'Add database indexes',
                    'Implement caching',
                    'Optimize queries',
                    'Use async operations'
                ]
            },
            'high_memory': {
                'threshold_mb': 500,
                'suggestions': [
                    'Clear unused variables',
                    'Use generators instead of lists',
                    'Implement pagination',
                    'Optimize image processing'
                ]
            },
            'frequent_errors': {
                'threshold_count': 10,
                'time_window_minutes': 5,
                'suggestions': [
                    'Add error handling',
                    'Implement retry logic',
                    'Add validation',
                    'Check dependencies'
                ]
            }
        }
    
    def _load_security_patterns(self) -> Dict[str, Any]:
        """Load security analysis patterns"""
        return {
            'sql_injection': {
                'patterns': [r'SELECT.*\+', r'UNION.*SELECT', r'DROP.*TABLE'],
                'severity': 'critical'
            },
            'xss_vulnerability': {
                'patterns': [r'<script>', r'javascript:', r'onerror='],
                'severity': 'high'
            },
            'path_traversal': {
                'patterns': [r'\.\./', r'\.\.\\', r'/etc/passwd'],
                'severity': 'high'
            },
            'exposed_secrets': {
                'patterns': [r'password\s*=\s*["\']', r'api_key\s*=\s*["\']', r'secret\s*=\s*["\']'],
                'severity': 'critical'
            }
        }
    
    def analyze_error(self, error_message: str, error_type: str = None, 
                     context: Dict = None) -> Dict[str, Any]:
        """Intelligently analyze an error and provide insights"""
        context = context or {}
        analysis = {
            'error_message': error_message,
            'error_type': error_type,
            'timestamp': datetime.now().isoformat(),
            'detected_patterns': [],
            'severity': 'unknown',
            'category': 'unknown',
            'confidence': 0.0,
            'fix_suggestions': [],
            'related_errors': [],
            'ai_insights': []
        }
        
        # Pattern matching
        error_lower = error_message.lower()
        for pattern_name, pattern_data in self.error_patterns.items():
            for pattern in pattern_data['patterns']:
                if re.search(pattern, error_lower, re.IGNORECASE):
                    analysis['detected_patterns'].append({
                        'pattern': pattern_name,
                        'matched': pattern,
                        'severity': pattern_data['severity'],
                        'category': pattern_data['category'],
                        'confidence': pattern_data['confidence']
                    })
                    
                    # Update overall analysis
                    if analysis['confidence'] < pattern_data['confidence']:
                        analysis['severity'] = pattern_data['severity']
                        analysis['category'] = pattern_data['category']
                        analysis['confidence'] = pattern_data['confidence']
        
        # Get fix suggestions
        if analysis['detected_patterns']:
            primary_pattern = analysis['detected_patterns'][0]['pattern']
            if primary_pattern in self.fix_suggestions:
                analysis['fix_suggestions'] = self.fix_suggestions[primary_pattern]
        
        # AI insights
        analysis['ai_insights'] = self._generate_ai_insights(error_message, context)
        
        # Related errors
        analysis['related_errors'] = self._find_related_errors(error_message)
        
        return analysis
    
    def _generate_ai_insights(self, error_message: str, context: Dict) -> List[str]:
        """Generate AI-powered insights about the error"""
        insights = []
        
        # Analyze error message structure
        if 'traceback' in error_message.lower():
            insights.append("🔍 Stack trace detected - check the last function call in traceback")
        
        if 'import' in error_message.lower() and 'error' in error_message.lower():
            insights.append("📦 Import error detected - verify package is installed: pip install <package>")
        
        if 'attribute' in error_message.lower():
            insights.append("🔧 Attribute error - object may not have expected method/property")
        
        if 'connection' in error_message.lower():
            insights.append("🌐 Connection issue - verify service is running and accessible")
        
        if 'permission' in error_message.lower() or 'access' in error_message.lower():
            insights.append("🔐 Permission issue - check file/directory permissions")
        
        # Context-based insights
        if context.get('endpoint'):
            insights.append(f"📍 Error occurred at endpoint: {context['endpoint']}")
        
        if context.get('method'):
            insights.append(f"🔀 HTTP method: {context['method']}")
        
        # Performance insights
        if context.get('response_time', 0) > 1000:
            insights.append("⏱️ Slow response detected - consider optimization")
        
        return insights
    
    def _find_related_errors(self, error_message: str) -> List[Dict]:
        """Find similar errors from error patterns"""
        related = []
        error_lower = error_message.lower()
        
        # Find similar patterns
        for pattern_name, pattern_data in self.error_patterns.items():
            similarity = self._calculate_similarity(error_lower, pattern_name)
            if similarity > 0.3:
                related.append({
                    'pattern': pattern_name,
                    'similarity': similarity,
                    'category': pattern_data['category']
                })
        
        return sorted(related, key=lambda x: x['similarity'], reverse=True)[:3]
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity between two strings"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union) if union else 0.0
    
    def analyze_endpoint_performance(self, endpoint: str, response_time: float,
                                    status_code: int, response_size: int) -> Dict[str, Any]:
        """Analyze endpoint performance and provide optimization suggestions"""
        analysis = {
            'endpoint': endpoint,
            'response_time_ms': response_time,
            'status_code': status_code,
            'response_size_bytes': response_size,
            'performance_score': 'good',
            'issues': [],
            'optimization_suggestions': []
        }
        
        # Check response time
        if response_time > self.performance_patterns['slow_response']['threshold_ms']:
            analysis['performance_score'] = 'slow'
            analysis['issues'].append('slow_response')
            analysis['optimization_suggestions'].extend(
                self.performance_patterns['slow_response']['suggestions']
            )
        
        # Check response size
        if response_size > 1024 * 1024:  # > 1MB
            analysis['issues'].append('large_response')
            analysis['optimization_suggestions'].append('Implement pagination or compression')
        
        # Check status code
        if status_code >= 500:
            analysis['performance_score'] = 'error'
            analysis['issues'].append('server_error')
        elif status_code >= 400:
            analysis['performance_score'] = 'warning'
            analysis['issues'].append('client_error')
        
        return analysis
    
    def generate_intelligent_tests(self, endpoint: str, method: str = 'GET') -> List[Dict]:
        """Generate intelligent test cases for an endpoint"""
        tests = []
        
        # Basic test
        tests.append({
            'name': f'{method} {endpoint} - Basic',
            'method': method,
            'url': endpoint,
            'headers': {},
            'body': {},
            'expected_status': 200 if method == 'GET' else [200, 201],
            'priority': 'high'
        })
        
        # Edge cases
        if method in ['POST', 'PUT']:
            # Empty body
            tests.append({
                'name': f'{method} {endpoint} - Empty Body',
                'method': method,
                'url': endpoint,
                'headers': {'Content-Type': 'application/json'},
                'body': {},
                'expected_status': [200, 201, 400],
                'priority': 'medium'
            })
            
            # Invalid JSON
            tests.append({
                'name': f'{method} {endpoint} - Invalid JSON',
                'method': method,
                'url': endpoint,
                'headers': {'Content-Type': 'application/json'},
                'body': 'invalid json',
                'expected_status': [400, 422],
                'priority': 'medium'
            })
        
        # Security tests
        if '/api/' in endpoint:
            # SQL injection attempt
            tests.append({
                'name': f'{method} {endpoint} - SQL Injection Test',
                'method': method,
                'url': endpoint + '?id=1\' OR \'1\'=\'1',
                'headers': {},
                'body': {},
                'expected_status': [400, 403, 500],
                'priority': 'high',
                'security_test': True
            })
        
        return tests
    
    def predict_errors(self, endpoint: str, method: str, 
                      historical_data: List[Dict] = None) -> Dict[str, Any]:
        """Predict potential errors based on patterns"""
        prediction = {
            'endpoint': endpoint,
            'method': method,
            'predicted_errors': [],
            'risk_score': 0.0,
            'confidence': 0.0
        }
        
        # Analyze endpoint pattern
        if '/api/' not in endpoint:
            prediction['predicted_errors'].append({
                'type': 'routing',
                'message': 'Endpoint may not be registered',
                'probability': 0.3
            })
        
        if method == 'POST' and '/create' not in endpoint and '/generate' not in endpoint:
            prediction['predicted_errors'].append({
                'type': 'method_mismatch',
                'message': 'POST method may not be appropriate',
                'probability': 0.2
            })
        
        # Historical analysis
        if historical_data:
            error_rate = sum(1 for d in historical_data if not d.get('success', True)) / len(historical_data)
            if error_rate > 0.1:
                prediction['risk_score'] = error_rate
                prediction['predicted_errors'].append({
                    'type': 'historical_pattern',
                    'message': f'High error rate detected: {error_rate:.1%}',
                    'probability': error_rate
                })
        
        # Calculate overall risk
        if prediction['predicted_errors']:
            prediction['risk_score'] = max(e['probability'] for e in prediction['predicted_errors'])
            prediction['confidence'] = 0.7
        
        return prediction
    
    def auto_fix_suggestion(self, error_analysis: Dict) -> Dict[str, Any]:
        """Generate automatic fix suggestion based on error analysis"""
        suggestion = {
            'can_auto_fix': False,
            'fix_steps': [],
            'estimated_time': 'unknown',
            'risk_level': 'unknown'
        }
        
        if not error_analysis.get('detected_patterns'):
            return suggestion
        
        primary_pattern = error_analysis['detected_patterns'][0]['pattern']
        
        # Auto-fixable patterns
        auto_fixable = {
            'method_not_allowed': {
                'can_auto_fix': True,
                'fix_steps': [
                    'Check route decorator for correct HTTP method',
                    'Update @route decorator to include method',
                    'Restart service'
                ],
                'estimated_time': '2 minutes',
                'risk_level': 'low'
            },
            '404_not_found': {
                'can_auto_fix': False,  # Requires manual verification
                'fix_steps': [
                    'Verify route exists in blueprint',
                    'Check URL prefix configuration',
                    'Verify blueprint is registered'
                ],
                'estimated_time': '5 minutes',
                'risk_level': 'medium'
            }
        }
        
        if primary_pattern in auto_fixable:
            suggestion.update(auto_fixable[primary_pattern])
        
        return suggestion


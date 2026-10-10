"""
Agent Event Listeners and Error Handlers System
Licensed from Law Paragraph System
Integrated with Agent Skillsets and CV
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import json

try:
    from src.db.models import db, Agent
    from src.db.models_agent_listeners import AgentEventListener, AgentErrorHandler
    from backend.services.rights_law_system import rights_law_system
except ImportError:
    db = None
    Agent = None
    AgentEventListener = None
    AgentErrorHandler = None
    rights_law_system = None


class AgentListenersHandlersSystem:
    """
    System for managing agent event listeners and error handlers
    Licensed from Law Paragraph System
    Integrated with agent skillsets and CV
    """
    
    # Predefined Event Listeners (5-6 types)
    EVENT_LISTENER_TYPES = {
        'task_completion': {
            'name': 'Task Completion Listener',
            'id': 'EL_TASK_COMPLETION_001',
            'design_model': 'Observer Pattern',
            'event_pattern': 'task.completed',
            'callback_function': 'on_task_completion',
            'law_paragraph_id': 'ur_003',  # Right to Fair Treatment
            'law_paragraph_category': 'rights',
            'description': 'Listens for task completion events and updates agent metrics'
        },
        'point_update': {
            'name': 'Point Update Listener',
            'id': 'EL_POINT_UPDATE_002',
            'design_model': 'Event-Driven Architecture',
            'event_pattern': 'points.updated',
            'callback_function': 'on_point_update',
            'law_paragraph_id': 'dp_001',  # Right to Access
            'law_paragraph_category': 'privacy',
            'description': 'Listens for point updates and maintains accurate records'
        },
        'error_detection': {
            'name': 'Error Detection Listener',
            'id': 'EL_ERROR_DETECTION_003',
            'design_model': 'Chain of Responsibility',
            'event_pattern': 'error.detected',
            'callback_function': 'on_error_detection',
            'law_paragraph_id': 'ur_004',  # Right to Appeal
            'law_paragraph_category': 'rights',
            'description': 'Listens for errors and triggers appropriate handlers'
        },
        'performance_metric': {
            'name': 'Performance Metric Listener',
            'id': 'EL_PERFORMANCE_METRIC_004',
            'design_model': 'Strategy Pattern',
            'event_pattern': 'performance.metric',
            'callback_function': 'on_performance_metric',
            'law_paragraph_id': 'ip_001',  # Copyright Protection
            'law_paragraph_category': 'ip',
            'description': 'Listens for performance metrics and updates agent statistics'
        },
        'user_interaction': {
            'name': 'User Interaction Listener',
            'id': 'EL_USER_INTERACTION_005',
            'design_model': 'Mediator Pattern',
            'event_pattern': 'user.interaction',
            'callback_function': 'on_user_interaction',
            'law_paragraph_id': 'ur_001',  # Right to Privacy
            'law_paragraph_category': 'rights',
            'description': 'Listens for user interactions and maintains privacy compliance'
        },
        'system_notification': {
            'name': 'System Notification Listener',
            'id': 'EL_SYSTEM_NOTIFICATION_006',
            'design_model': 'Publisher-Subscriber Pattern',
            'event_pattern': 'system.notification',
            'callback_function': 'on_system_notification',
            'law_paragraph_id': 'ur_005',  # Right to Information
            'law_paragraph_category': 'rights',
            'description': 'Listens for system notifications and ensures information rights'
        }
    }
    
    # Predefined Error Handlers (5-6 types)
    ERROR_HANDLER_TYPES = {
        'exception_handler': {
            'name': 'Exception Handler',
            'id': 'EH_EXCEPTION_001',
            'design_model': 'Exception Handling Pattern',
            'error_pattern': 'exception.*',
            'error_types': ['ValueError', 'TypeError', 'KeyError', 'AttributeError'],
            'recovery_strategy': 'graceful_degradation',
            'law_paragraph_id': 'ur_004',  # Right to Appeal
            'law_paragraph_category': 'rights',
            'description': 'Handles exceptions and provides recovery mechanisms'
        },
        'validation_handler': {
            'name': 'Validation Handler',
            'id': 'EH_VALIDATION_002',
            'design_model': 'Validator Pattern',
            'error_pattern': 'validation.*',
            'error_types': ['ValidationError', 'InvalidInputError'],
            'recovery_strategy': 'input_correction',
            'law_paragraph_id': 'dp_002',  # Right to Rectification
            'law_paragraph_category': 'privacy',
            'description': 'Handles validation errors and corrects invalid inputs'
        },
        'data_integrity_handler': {
            'name': 'Data Integrity Handler',
            'id': 'EH_DATA_INTEGRITY_003',
            'design_model': 'Data Integrity Pattern',
            'error_pattern': 'data.integrity.*',
            'error_types': ['DataIntegrityError', 'CorruptionError'],
            'recovery_strategy': 'data_restoration',
            'law_paragraph_id': 'dp_004',  # Right to Data Portability
            'law_paragraph_category': 'privacy',
            'description': 'Handles data integrity issues and restores corrupted data'
        },
        'network_error_handler': {
            'name': 'Network Error Handler',
            'id': 'EH_NETWORK_ERROR_004',
            'design_model': 'Retry Pattern',
            'error_pattern': 'network.*',
            'error_types': ['ConnectionError', 'TimeoutError', 'NetworkError'],
            'recovery_strategy': 'retry_with_backoff',
            'law_paragraph_id': 'platform_001',  # Service Availability
            'law_paragraph_category': 'platform',
            'description': 'Handles network errors with retry mechanisms'
        },
        'authentication_handler': {
            'name': 'Authentication Handler',
            'id': 'EH_AUTHENTICATION_005',
            'design_model': 'Security Pattern',
            'error_pattern': 'authentication.*',
            'error_types': ['AuthenticationError', 'AuthorizationError'],
            'recovery_strategy': 're_authentication',
            'law_paragraph_id': 'ur_001',  # Right to Privacy
            'law_paragraph_category': 'rights',
            'description': 'Handles authentication errors and maintains security'
        },
        'resource_handler': {
            'name': 'Resource Handler',
            'id': 'EH_RESOURCE_006',
            'design_model': 'Resource Management Pattern',
            'error_pattern': 'resource.*',
            'error_types': ['ResourceError', 'MemoryError', 'DiskError'],
            'recovery_strategy': 'resource_cleanup',
            'law_paragraph_id': 'platform_001',  # Service Availability
            'law_paragraph_category': 'platform',
            'description': 'Handles resource errors and manages system resources'
        }
    }
    
    def __init__(self):
        """Initialize the system"""
        pass
    
    def attach_listeners_to_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Attach all predefined event listeners to an agent
        
        Returns:
            Dictionary with attached listeners
        """
        if not db or not AgentEventListener:
            return {'success': False, 'error': 'Database not available'}
        
        attached_listeners = []
        
        for listener_type, listener_config in self.EVENT_LISTENER_TYPES.items():
            try:
                # Check if already exists
                existing = AgentEventListener.query.filter_by(
                    agent_id=agent_id,
                    listener_id=listener_config['id']
                ).first()
                
                if existing:
                    attached_listeners.append(existing.to_dict())
                    continue
                
                # Get law paragraph license
                license_info = self._get_law_paragraph_license(
                    listener_config['law_paragraph_id'],
                    listener_config['law_paragraph_category']
                )
                
                # Create listener
                listener = AgentEventListener(
                    id=str(uuid.uuid4()),
                    agent_id=agent_id,
                    listener_name=listener_config['name'],
                    listener_id=listener_config['id'],
                    listener_type=listener_type,
                    design_model=listener_config['design_model'],
                    design_version='1.0.0',
                    law_paragraph_id=listener_config['law_paragraph_id'],
                    law_paragraph_category=listener_config['law_paragraph_category'],
                    license_granted=license_info.get('granted', True),
                    license_date=datetime.utcnow(),
                    license_terms=json.dumps(license_info.get('terms', {})),
                    event_pattern=listener_config['event_pattern'],
                    callback_function=listener_config['callback_function'],
                    priority=5,
                    is_active=True
                )
                
                db.session.add(listener)
                attached_listeners.append(listener.to_dict())
                
            except Exception as e:
                print(f"[AgentListeners] Error attaching listener {listener_type}: {e}", flush=True)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
        
        # Update agent skillsets and CV
        self._update_agent_skillsets(agent_id, attached_listeners, 'listeners')
        
        return {
            'success': True,
            'agent_id': agent_id,
            'listeners_attached': len(attached_listeners),
            'listeners': attached_listeners
        }
    
    def attach_handlers_to_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Attach all predefined error handlers to an agent
        
        Returns:
            Dictionary with attached handlers
        """
        if not db or not AgentErrorHandler:
            return {'success': False, 'error': 'Database not available'}
        
        attached_handlers = []
        
        for handler_type, handler_config in self.ERROR_HANDLER_TYPES.items():
            try:
                # Check if already exists
                existing = AgentErrorHandler.query.filter_by(
                    agent_id=agent_id,
                    handler_id=handler_config['id']
                ).first()
                
                if existing:
                    attached_handlers.append(existing.to_dict())
                    continue
                
                # Get law paragraph license
                license_info = self._get_law_paragraph_license(
                    handler_config['law_paragraph_id'],
                    handler_config['law_paragraph_category']
                )
                
                # Create handler
                handler = AgentErrorHandler(
                    id=str(uuid.uuid4()),
                    agent_id=agent_id,
                    handler_name=handler_config['name'],
                    handler_id=handler_config['id'],
                    handler_type=handler_type,
                    design_model=handler_config['design_model'],
                    design_version='1.0.0',
                    law_paragraph_id=handler_config['law_paragraph_id'],
                    law_paragraph_category=handler_config['law_paragraph_category'],
                    license_granted=license_info.get('granted', True),
                    license_date=datetime.utcnow(),
                    license_terms=json.dumps(license_info.get('terms', {})),
                    error_pattern=handler_config['error_pattern'],
                    error_types=json.dumps(handler_config['error_types']),
                    recovery_strategy=handler_config['recovery_strategy'],
                    priority=5,
                    is_active=True
                )
                
                db.session.add(handler)
                attached_handlers.append(handler.to_dict())
                
            except Exception as e:
                print(f"[AgentHandlers] Error attaching handler {handler_type}: {e}", flush=True)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
        
        # Update agent skillsets and CV
        self._update_agent_skillsets(agent_id, attached_handlers, 'handlers')
        
        return {
            'success': True,
            'agent_id': agent_id,
            'handlers_attached': len(attached_handlers),
            'handlers': attached_handlers
        }
    
    def _get_law_paragraph_license(self, paragraph_id: str, category: str) -> Dict[str, Any]:
        """Get license information from law paragraph system"""
        if not rights_law_system:
            return {
                'granted': True,
                'terms': {
                    'paragraph_id': paragraph_id,
                    'category': category,
                    'license_type': 'standard',
                    'granted_at': datetime.utcnow().isoformat()
                }
            }
        
        try:
            # Get paragraph from rights law system
            paragraphs = rights_law_system.get_all_paragraphs()
            paragraph = None
            
            for cat_data in paragraphs.get('categories', []):
                if cat_data.get('id') == category:
                    for para in cat_data.get('paragraphs', []):
                        if para.get('id') == paragraph_id:
                            paragraph = para
                            break
            
            if paragraph:
                return {
                    'granted': True,
                    'terms': {
                        'paragraph_id': paragraph_id,
                        'paragraph_title': paragraph.get('title', ''),
                        'category': category,
                        'points_value': paragraph.get('points_value', 0),
                        'license_type': 'law_paragraph_license',
                        'granted_at': datetime.utcnow().isoformat(),
                        'compliance': True
                    }
                }
        except Exception as e:
            print(f"[AgentListeners] Error getting law paragraph license: {e}", flush=True)
        
        return {
            'granted': True,
            'terms': {
                'paragraph_id': paragraph_id,
                'category': category,
                'license_type': 'standard',
                'granted_at': datetime.utcnow().isoformat()
            }
        }
    
    def _update_agent_skillsets(self, agent_id: str, items: List[Dict], item_type: str):
        """Update agent skillsets and CV with listeners/handlers"""
        if not db or not Agent:
            return
        
        try:
            agent = Agent.query.filter_by(id=agent_id).first()
            if not agent:
                return
            
            import json
            
            # Get current capabilities
            capabilities = json.loads(agent.capabilities) if agent.capabilities else []
            
            # Add to capabilities
            for item in items:
                skill_entry = {
                    'type': item_type,
                    'name': item.get('listener_name') or item.get('handler_name'),
                    'id': item.get('listener_id') or item.get('handler_id'),
                    'design_model': item.get('design_model'),
                    'law_paragraph_id': item.get('law_paragraph_id'),
                    'law_paragraph_category': item.get('law_paragraph_category'),
                    'license_granted': item.get('license_granted', True),
                    'added_at': datetime.utcnow().isoformat()
                }
                capabilities.append(skill_entry)
            
            # Update agent
            agent.capabilities = json.dumps(capabilities)
            agent.updated_at = datetime.utcnow()
            
            db.session.commit()
            
        except Exception as e:
            print(f"[AgentListeners] Error updating agent skillsets: {e}", flush=True)
            db.session.rollback()
    
    def get_agent_listeners(self, agent_id: str) -> Dict[str, Any]:
        """Get all listeners for an agent"""
        if not db or not AgentEventListener:
            return {'success': False, 'listeners': []}
        
        listeners = AgentEventListener.query.filter_by(agent_id=agent_id).all()
        return {
            'success': True,
            'agent_id': agent_id,
            'listeners': [l.to_dict() for l in listeners],
            'count': len(listeners)
        }
    
    def get_agent_handlers(self, agent_id: str) -> Dict[str, Any]:
        """Get all handlers for an agent"""
        if not db or not AgentErrorHandler:
            return {'success': False, 'handlers': []}
        
        handlers = AgentErrorHandler.query.filter_by(agent_id=agent_id).all()
        return {
            'success': True,
            'agent_id': agent_id,
            'handlers': [h.to_dict() for h in handlers],
            'count': len(handlers)
        }
    
    def get_agent_cv(self, agent_id: str) -> Dict[str, Any]:
        """Get complete agent CV including listeners and handlers"""
        if not db or not Agent:
            return {'success': False, 'error': 'Agent not found'}
        
        agent = Agent.query.filter_by(id=agent_id).first()
        if not agent:
            return {'success': False, 'error': 'Agent not found'}
        
        listeners = self.get_agent_listeners(agent_id)
        handlers = self.get_agent_handlers(agent_id)
        
        import json
        
        return {
            'success': True,
            'agent_id': agent_id,
            'agent_name': agent.name,
            'agent_type': agent.agent_type,
            'capabilities': json.loads(agent.capabilities) if agent.capabilities else [],
            'specializations': json.loads(agent.specializations) if agent.specializations else [],
            'event_listeners': listeners.get('listeners', []),
            'error_handlers': handlers.get('handlers', []),
            'listeners_count': listeners.get('count', 0),
            'handlers_count': handlers.get('count', 0),
            'total_skills': listeners.get('count', 0) + handlers.get('count', 0),
            'performance': {
                'tasks_completed': agent.tasks_completed,
                'success_rate': agent.success_rate,
                'average_response_time': agent.average_response_time
            }
        }


# Global instance
agent_listeners_handlers = AgentListenersHandlersSystem()


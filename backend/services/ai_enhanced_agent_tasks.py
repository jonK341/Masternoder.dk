"""
AI-Enhanced Agent Tasks
Adds AI intelligence to agent task management
"""
from typing import Dict, List, Optional
from datetime import datetime
from backend.services.agent_ai_intelligence import agent_ai_intelligence


class AIEnhancedAgentTasks:
    """AI-enhanced agent task management"""
    
    def __init__(self):
        self.ai = agent_ai_intelligence
    
    def intelligent_task_assignment(self, task_data: Dict, available_agents: List[str]) -> Dict:
        """Intelligently assign task to best agent using AI"""
        # Use AI to make decision about task assignment
        options = []
        for agent_id in available_agents:
            # Get agent intelligence
            agent_intel = self.ai.get_agent_intelligence(agent_id)
            success_rate = agent_intel.get('success_rate', 50)
            
            options.append({
                'action': 'assign',
                'agent_id': agent_id,
                'benefit': success_rate / 100.0,
                'cost': 0.2,
                'agent_intelligence': agent_intel
            })
        
        # Use AI decision making
        decision = self.ai.make_decision(
            agent_id='task_assigner',
            context={
                'task_type': task_data.get('task_type'),
                'priority': task_data.get('priority', 'medium'),
                'tab': task_data.get('tab')
            },
            options=options,
            strategy='balanced'
        )
        
        return {
            'recommended_agent': decision.get('decision', {}).get('agent_id') if decision.get('decision') else available_agents[0] if available_agents else None,
            'confidence': decision.get('confidence', 0.5),
            'decision': decision,
            'all_options': options
        }
    
    def predict_task_success(self, task_data: Dict) -> Dict:
        """Predict task success likelihood using AI"""
        # Use AI to predict
        prediction = self.ai.predict_outcome(
            agent_id='task_predictor',
            action={'type': 'complete_task', 'task_data': task_data},
            context={
                'task_type': task_data.get('task_type'),
                'priority': task_data.get('priority', 'medium'),
                'tab': task_data.get('tab')
            }
        )
        
        return {
            'task_data': task_data,
            'prediction': prediction,
            'success_likelihood': prediction.get('prediction_score', 0.5),
            'recommendations': self._generate_task_recommendations(task_data, prediction)
        }
    
    def optimize_task_execution(self, task_data: Dict, session_data: Dict) -> Dict:
        """Optimize task execution using AI"""
        # Use AI to develop optimization strategy
        strategy = self.ai.develop_strategy(
            agent_id='task_optimizer',
            goal='optimize_task_execution',
            constraints={
                'task_type': task_data.get('task_type'),
                'session_actions': session_data.get('actions_count', 0),
                'session_errors': session_data.get('errors_count', 0)
            }
        )
        
        # Use AI to optimize decisions
        decisions = [
            {'action': 'execute_now', 'benefit': 0.8, 'cost': 0.2},
            {'action': 'defer', 'benefit': 0.4, 'cost': 0.1},
            {'action': 'optimize_first', 'benefit': 0.9, 'cost': 0.3}
        ]
        
        optimized = self.ai.optimize_decision(
            agent_id='task_optimizer',
            decisions=decisions,
            constraints={'max_decisions': 1}
        )
        
        return {
            'strategy': strategy,
            'optimized_decision': optimized,
            'recommendations': [phase.get('action') for phase in strategy.get('phases', [])]
        }
    
    def _generate_task_recommendations(self, task_data: Dict, prediction: Dict) -> List[str]:
        """Generate AI-powered task recommendations"""
        recommendations = []
        
        success_likelihood = prediction.get('prediction_score', 0.5)
        
        if success_likelihood < 0.5:
            recommendations.append('Low success likelihood - consider breaking task into smaller parts')
        
        if task_data.get('priority') == 'high':
            recommendations.append('High priority task - allocate additional resources')
        
        # Use AI to develop recommendations
        strategy = self.ai.develop_strategy(
            agent_id='task_recommender',
            goal='improve_task_success',
            constraints={'task_data': task_data}
        )
        
        for phase in strategy.get('phases', []):
            recommendations.append(f"Phase {phase.get('phase')}: {phase.get('action')}")
        
        return recommendations

    def enhance_task_assignment(self, task_data: Dict, agent_id: str) -> Dict:
        """LLM-enhanced task assignment hint via agent_ai_router (log_triage task_kind)."""
        tab = task_data.get("tab") or ""
        action = task_data.get("action") or ""
        description = task_data.get("description") or f"{tab} — {action}"
        try:
            from backend.services.agent_ai_router import routed_chat

            messages = [
                {
                    "role": "user",
                    "content": (
                        f"Debugger task for agent {agent_id}.\n"
                        f"Tab: {tab}\nAction: {action}\nDescription: {description}\n\n"
                        "In 2-4 sentences: priority, risks, and first step."
                    ),
                }
            ]
            resp, routing = routed_chat(
                messages,
                "log_triage",
                "system",
                temperature=0.25,
                max_tokens=220,
            )
            return {
                "ai_enhanced": True,
                "agent_id": agent_id,
                "task_id": task_data.get("task_id"),
                "routing": routing,
                "suggestion": (resp.content or "").strip() if resp.success else None,
                "llm_success": bool(resp.success),
                "provider": resp.provider,
            }
        except Exception as e:
            return {
                "ai_enhanced": False,
                "agent_id": agent_id,
                "error": str(e)[:200],
                "fallback": self.intelligent_task_assignment(task_data, [agent_id]),
            }


# Global instance
ai_enhanced_agent_tasks = AIEnhancedAgentTasks()

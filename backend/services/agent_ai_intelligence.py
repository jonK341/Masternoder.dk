"""
Agent AI Intelligence Service
Advanced AI intelligence capabilities for agents including decision making,
learning, prediction, pattern recognition, and adaptive behavior
"""
import os
import json
import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentAIIntelligence:
    """AI Intelligence system for agents"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.intelligence_file = os.path.join(self.base_dir, 'logs', 'agent_ai_intelligence', 'intelligence.json')
        self.load_intelligence()
    
    def load_intelligence(self):
        """Load intelligence data"""
        os.makedirs(os.path.dirname(self.intelligence_file), exist_ok=True)
        if os.path.exists(self.intelligence_file):
            try:
                with open(self.intelligence_file, 'r') as f:
                    self.intelligence = json.load(f)
            except:
                self.intelligence = self._default_intelligence()
        else:
            self.intelligence = self._default_intelligence()
            self.save_intelligence()
    
    def _serializable_copy(self, obj: Any, depth: int = 0, _max_depth: int = 5) -> Any:
        """Return a JSON-serializable copy of obj to avoid circular refs / recursion in save_intelligence."""
        if depth > _max_depth:
            return None
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
        if isinstance(obj, dict):
            return {str(k): self._serializable_copy(v, depth + 1, _max_depth) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._serializable_copy(x, depth + 1, _max_depth) for x in obj]
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return str(type(obj).__name__)
    
    def _default_intelligence(self) -> Dict:
        """Default intelligence data"""
        return {
            'agents': {},
            'knowledge_base': {},
            'patterns': {},
            'predictions': {},
            'decisions': [],
            'learning_history': [],
            'strategies': {},
            'risk_assessments': {},
            'optimizations': {},
            'context_understanding': {},
            'unified_points_context': {},
            'content_generation': {},
            'power_level': 100,
            'enhanced_capabilities': {
                'decision_power': 10,
                'prediction_power': 10,
                'content_power': 10,
                'optimization_power': 10
            },
            'last_updated': datetime.now().isoformat()
        }
    
    def save_intelligence(self):
        """Save intelligence data. Uses serializable copy to avoid recursion in json.dump; never logs recursion."""
        try:
            self.intelligence['last_updated'] = datetime.now().isoformat()
            # Dump a serializable copy so json.dump never hits circular refs / recursion
            data = self._serializable_copy(self.intelligence)
            if data is None:
                return
            with open(self.intelligence_file, 'w') as f:
                json.dump(data, f, indent=2)
        except RecursionError:
            pass
        except Exception as e:
            if "recursion" in str(e).lower():
                pass
            else:
                print(f"Error saving intelligence: {e}")
    
    def make_decision(self, agent_id: str, context: Dict, options: List[Dict], strategy: str = 'balanced') -> Dict:
        """Make an intelligent decision based on context and options"""
        if agent_id not in self.intelligence['agents']:
            self.intelligence['agents'][agent_id] = {
                'decisions_made': 0,
                'successful_decisions': 0,
                'decision_history': [],
                'preferences': {},
                'learning_data': {}
            }
        
        agent_data = self.intelligence['agents'][agent_id]
        
        # Enhance context with unified points if available
        if 'unified_points' not in context:
            try:
                from backend.services.ai_agent_class import get_ai_agent
                ai_agent = get_ai_agent(agent_id)
                points_context = ai_agent.get_unified_points_context()
                context['unified_points'] = points_context
            except:
                pass
        
        # Apply enhanced power
        power_level = agent_data.get('power_level', 10)
        enhanced_power = self.intelligence.get('enhanced_capabilities', {}).get('decision_power', 10)
        total_power = power_level + enhanced_power
        
        # Analyze options using intelligence with enhanced power
        scored_options = []
        for option in options:
            base_score = self._score_option(option, context, agent_data, strategy)
            # Apply power multiplier
            enhanced_score = base_score * (1 + (total_power / 100.0))
            scored_options.append({
                'option': option,
                'score': min(1.0, enhanced_score),
                'confidence': self._calculate_confidence(enhanced_score, context),
                'power_applied': total_power
            })
        
        # Sort by score
        scored_options.sort(key=lambda x: x['score'], reverse=True)
        best_option = scored_options[0] if scored_options else None
        
        # Store only JSON-serializable data to avoid recursion when saving (context/options may have circular refs)
        decision = {
            'agent_id': agent_id,
            'context': self._serializable_copy(context),
            'decision': self._serializable_copy(best_option['option']) if best_option else None,
            'score': best_option['score'] if best_option else 0,
            'confidence': best_option['confidence'] if best_option else 0,
            'all_options': [{'option': self._serializable_copy(s['option']), 'score': s['score'], 'confidence': s['confidence'], 'power_applied': s['power_applied']} for s in scored_options],
            'strategy': strategy,
            'power_applied': total_power,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store decision
        agent_data['decisions_made'] = agent_data.get('decisions_made', 0) + 1
        agent_data['decision_history'].append(decision)
        if len(agent_data['decision_history']) > 100:
            agent_data['decision_history'] = agent_data['decision_history'][-100:]
        
        self.intelligence['decisions'].append(decision)
        if len(self.intelligence['decisions']) > 1000:
            self.intelligence['decisions'] = self.intelligence['decisions'][-1000:]
        
        self.save_intelligence()
        return decision

    def llm_insight(
        self,
        agent_id: str,
        topic: str,
        context: Optional[Dict] = None,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Optional LLM-backed insight using configured providers (defaults to free-tier routing).
        Falls back gracefully when no LLM is available.
        """
        ctx = context or {}
        tt = task_type or os.environ.get("AGENT_AI_LLM_TASK", "free").strip() or "free"
        try:
            from backend.services.llm_service import complete, is_available
        except Exception:
            return {
                "success": False,
                "agent_id": agent_id,
                "topic": topic,
                "error": "llm_service unavailable",
                "insight": None,
            }

        if not is_available():
            return {
                "success": False,
                "agent_id": agent_id,
                "topic": topic,
                "error": "No LLM API keys configured — add GROQ_API_KEY or GOOGLE_AI_API_KEY in .env",
                "insight": None,
            }

        prompt = (
            f"Agent: {agent_id}\nTopic: {topic}\nContext (JSON):\n"
            f"{json.dumps(self._serializable_copy(ctx), indent=2)[:12000]}\n\n"
            "Give a concise tactical insight (under 400 words): risks, next steps, one clear recommendation."
        )
        resp = complete(
            prompt=prompt,
            system_prompt=(
                "You are the strategic intelligence layer for MasterNoder.dk agents. "
                "Be specific and actionable. No markdown code fences."
            ),
            temperature=0.35,
            max_tokens=700,
            task_type=tt,
        )
        out: Dict[str, Any] = {
            "success": bool(resp.success),
            "agent_id": agent_id,
            "topic": topic,
            "task_type": tt,
            "provider": resp.provider,
            "model": resp.model,
            "insight": (resp.content or "").strip() if resp.success else None,
            "error": resp.error if not resp.success else None,
            "timestamp": datetime.now().isoformat(),
        }
        return out
    
    def _score_option(self, option: Dict, context: Dict, agent_data: Dict, strategy: str) -> float:
        """Score an option based on intelligence factors"""
        score = 0.5  # Base score
        
        # Factor 1: Past success (learn from history)
        past_success = self._get_past_success_rate(option, agent_data)
        score += past_success * 0.3
        
        # Factor 2: Risk assessment
        risk = self._assess_risk(option, context)
        if strategy == 'cautious':
            score += (1 - risk) * 0.3
        elif strategy == 'aggressive':
            score += risk * 0.2
        else:
            score += (1 - risk) * 0.15
        
        # Factor 3: Context relevance
        relevance = self._calculate_relevance(option, context)
        score += relevance * 0.25
        
        # Factor 4: Resource efficiency
        efficiency = self._calculate_efficiency(option, context)
        score += efficiency * 0.15
        
        return min(1.0, max(0.0, score))
    
    def _get_past_success_rate(self, option: Dict, agent_data: Dict) -> float:
        """Get past success rate for similar options"""
        history = agent_data.get('decision_history', [])
        if not history:
            return 0.5
        
        # Simple similarity check
        similar_decisions = [d for d in history if self._options_similar(d.get('decision', {}), option)]
        if not similar_decisions:
            return 0.5
        
        # Calculate success rate (assuming decisions with high confidence were successful)
        successful = sum(1 for d in similar_decisions if d.get('confidence', 0) > 0.7)
        return successful / len(similar_decisions) if similar_decisions else 0.5
    
    def _options_similar(self, option1: Dict, option2: Dict) -> bool:
        """Check if two options are similar"""
        # Simple similarity check - can be enhanced
        return option1.get('type') == option2.get('type')
    
    def _assess_risk(self, option: Dict, context: Dict) -> float:
        """Assess risk level of an option (0-1, where 1 is highest risk)"""
        # Simple risk assessment
        risk_factors = option.get('risk_factors', [])
        if not risk_factors:
            return 0.3  # Default moderate risk
        
        return min(1.0, len(risk_factors) * 0.2)
    
    def _calculate_relevance(self, option: Dict, context: Dict) -> float:
        """Calculate how relevant an option is to the context"""
        # Simple relevance calculation
        context_keys = set(context.keys())
        option_keys = set(option.keys())
        overlap = len(context_keys.intersection(option_keys))
        return min(1.0, overlap / max(len(context_keys), 1))
    
    def _calculate_efficiency(self, option: Dict, context: Dict) -> float:
        """Calculate efficiency score"""
        # Simple efficiency calculation
        cost = option.get('cost', 1)
        benefit = option.get('benefit', 1)
        return min(1.0, benefit / max(cost, 1))
    
    def _calculate_confidence(self, score: float, context: Dict) -> float:
        """Calculate confidence level for decision"""
        # Confidence increases with score and context completeness
        context_completeness = len(context) / 10.0  # Normalize
        confidence = (score * 0.7) + (min(1.0, context_completeness) * 0.3)
        return min(1.0, max(0.0, confidence))
    
    def learn_from_experience(self, agent_id: str, experience: Dict) -> Dict:
        """Learn from experience and update knowledge"""
        if agent_id not in self.intelligence['agents']:
            self.intelligence['agents'][agent_id] = {
                'decisions_made': 0,
                'successful_decisions': 0,
                'decision_history': [],
                'preferences': {},
                'learning_data': {}
            }
        
        agent_data = self.intelligence['agents'][agent_id]
        learning_data = agent_data.get('learning_data', {})
        
        # Extract patterns from experience
        outcome = experience.get('outcome', 'neutral')
        action = experience.get('action', {})
        context = experience.get('context', {})
        
        # Update preferences based on outcomes
        if outcome == 'success':
            agent_data['successful_decisions'] = agent_data.get('successful_decisions', 0) + 1
            # Reinforce successful patterns
            for key, value in context.items():
                if key not in learning_data:
                    learning_data[key] = {'success_count': 0, 'failure_count': 0}
                learning_data[key]['success_count'] = learning_data[key].get('success_count', 0) + 1
        elif outcome == 'failure':
            # Learn from failures
            for key, value in context.items():
                if key not in learning_data:
                    learning_data[key] = {'success_count': 0, 'failure_count': 0}
                learning_data[key]['failure_count'] = learning_data[key].get('failure_count', 0) + 1
        
        agent_data['learning_data'] = learning_data
        
        # Store learning history (serializable copy to avoid recursion on save)
        learning_entry = {
            'agent_id': agent_id,
            'experience': self._serializable_copy(experience),
            'timestamp': datetime.now().isoformat()
        }
        agent_data.get('decision_history', []).append(learning_entry)
        self.intelligence['learning_history'].append(learning_entry)
        if len(self.intelligence['learning_history']) > 1000:
            self.intelligence['learning_history'] = self.intelligence['learning_history'][-1000:]
        
        self.save_intelligence()
        return {'success': True, 'learned': True}
    
    def predict_outcome(self, agent_id: str, action: Dict, context: Dict) -> Dict:
        """Predict the outcome of an action"""
        agent_data = self.intelligence['agents'].get(agent_id, {})
        learning_data = agent_data.get('learning_data', {})
        
        # Use historical data to predict
        prediction_score = 0.5
        confidence = 0.5
        
        # Analyze similar past actions
        similar_actions = [d for d in agent_data.get('decision_history', []) 
                          if self._options_similar(d.get('decision', {}), action)]
        
        if similar_actions:
            # Calculate average success rate
            success_rate = sum(1 for d in similar_actions if d.get('confidence', 0) > 0.7) / len(similar_actions)
            prediction_score = success_rate
            confidence = min(1.0, len(similar_actions) / 10.0)
        
        prediction = {
            'agent_id': agent_id,
            'action': action,
            'predicted_outcome': 'success' if prediction_score > 0.6 else 'failure' if prediction_score < 0.4 else 'neutral',
            'prediction_score': prediction_score,
            'confidence': confidence,
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store prediction
        if agent_id not in self.intelligence['predictions']:
            self.intelligence['predictions'][agent_id] = []
        self.intelligence['predictions'][agent_id].append(prediction)
        if len(self.intelligence['predictions'][agent_id]) > 100:
            self.intelligence['predictions'][agent_id] = self.intelligence['predictions'][agent_id][-100:]
        
        self.save_intelligence()
        return prediction
    
    def recognize_pattern(self, agent_id: str, data: List[Dict], pattern_type: str = 'sequence') -> Dict:
        """Recognize patterns in data"""
        patterns = []
        
        if pattern_type == 'sequence':
            # Detect sequential patterns
            if len(data) >= 3:
                sequences = defaultdict(int)
                for i in range(len(data) - 2):
                    seq = (data[i].get('type'), data[i+1].get('type'), data[i+2].get('type'))
                    sequences[seq] += 1
                
                # Find frequent sequences
                for seq, count in sequences.items():
                    if count >= 2:
                        patterns.append({
                            'type': 'sequence',
                            'pattern': seq,
                            'frequency': count,
                            'confidence': count / len(data)
                        })
        
        elif pattern_type == 'trend':
            # Detect trends
            values = [d.get('value', 0) for d in data if 'value' in d]
            if len(values) >= 3:
                trend = 'increasing' if values[-1] > values[0] else 'decreasing' if values[-1] < values[0] else 'stable'
                patterns.append({
                    'type': 'trend',
                    'trend': trend,
                    'strength': abs(values[-1] - values[0]) / max(abs(max(values)), abs(min(values)), 1),
                    'confidence': min(1.0, len(values) / 10.0)
                })
        
        # Store patterns
        if agent_id not in self.intelligence['patterns']:
            self.intelligence['patterns'][agent_id] = []
        self.intelligence['patterns'][agent_id].extend(patterns)
        if len(self.intelligence['patterns'][agent_id]) > 100:
            self.intelligence['patterns'][agent_id] = self.intelligence['patterns'][agent_id][-100:]
        
        self.save_intelligence()
        return {'patterns': patterns, 'count': len(patterns)}
    
    def develop_strategy(self, agent_id: str, goal: str, constraints: Dict = None) -> Dict:
        """Develop an intelligent strategy to achieve a goal"""
        strategy_id = f"{agent_id}_{goal}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Analyze goal and constraints
        strategy = {
            'strategy_id': strategy_id,
            'agent_id': agent_id,
            'goal': goal,
            'constraints': constraints or {},
            'phases': [],
            'risk_level': 'moderate',
            'estimated_success': 0.7,
            'created_at': datetime.now().isoformat()
        }
        
        # Generate strategy phases based on goal
        if 'optimize' in goal.lower():
            strategy['phases'] = [
                {'phase': 1, 'action': 'analyze_current_state', 'priority': 'high'},
                {'phase': 2, 'action': 'identify_optimizations', 'priority': 'high'},
                {'phase': 3, 'action': 'implement_changes', 'priority': 'medium'},
                {'phase': 4, 'action': 'monitor_results', 'priority': 'medium'}
            ]
        elif 'fix' in goal.lower() or 'repair' in goal.lower():
            strategy['phases'] = [
                {'phase': 1, 'action': 'diagnose_issue', 'priority': 'high'},
                {'phase': 2, 'action': 'identify_root_cause', 'priority': 'high'},
                {'phase': 3, 'action': 'apply_fix', 'priority': 'high'},
                {'phase': 4, 'action': 'verify_fix', 'priority': 'medium'}
            ]
        else:
            # Generic strategy
            strategy['phases'] = [
                {'phase': 1, 'action': 'plan', 'priority': 'high'},
                {'phase': 2, 'action': 'execute', 'priority': 'high'},
                {'phase': 3, 'action': 'monitor', 'priority': 'medium'},
                {'phase': 4, 'action': 'optimize', 'priority': 'low'}
            ]
        
        # Store strategy
        if agent_id not in self.intelligence['strategies']:
            self.intelligence['strategies'][agent_id] = []
        self.intelligence['strategies'][agent_id].append(strategy)
        if len(self.intelligence['strategies'][agent_id]) > 50:
            self.intelligence['strategies'][agent_id] = self.intelligence['strategies'][agent_id][-50:]
        
        self.save_intelligence()
        return strategy
    
    def assess_risk(self, agent_id: str, scenario: Dict) -> Dict:
        """Assess risk for a scenario"""
        risk_factors = []
        risk_score = 0.0
        
        # Analyze scenario for risk factors
        if scenario.get('uncertainty', 0) > 0.5:
            risk_factors.append('high_uncertainty')
            risk_score += 0.3
        
        if scenario.get('complexity', 0) > 0.7:
            risk_factors.append('high_complexity')
            risk_score += 0.2
        
        if scenario.get('resource_constraints', False):
            risk_factors.append('resource_constraints')
            risk_score += 0.2
        
        if scenario.get('time_pressure', False):
            risk_factors.append('time_pressure')
            risk_score += 0.2
        
        if scenario.get('dependencies', 0) > 5:
            risk_factors.append('many_dependencies')
            risk_score += 0.1
        
        risk_level = 'low' if risk_score < 0.3 else 'moderate' if risk_score < 0.6 else 'high'
        
        assessment = {
            'agent_id': agent_id,
            'scenario': self._serializable_copy(scenario),
            'risk_score': min(1.0, risk_score),
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'recommendations': self._generate_risk_recommendations(risk_factors),
            'timestamp': datetime.now().isoformat()
        }
        
        # Store assessment
        if agent_id not in self.intelligence['risk_assessments']:
            self.intelligence['risk_assessments'][agent_id] = []
        self.intelligence['risk_assessments'][agent_id].append(assessment)
        if len(self.intelligence['risk_assessments'][agent_id]) > 100:
            self.intelligence['risk_assessments'][agent_id] = self.intelligence['risk_assessments'][agent_id][-100:]
        
        self.save_intelligence()
        return assessment
    
    def _generate_risk_recommendations(self, risk_factors: List[str]) -> List[str]:
        """Generate recommendations based on risk factors"""
        recommendations = []
        factor_recommendations = {
            'high_uncertainty': 'Gather more information before proceeding',
            'high_complexity': 'Break down into smaller, manageable tasks',
            'resource_constraints': 'Prioritize critical resources',
            'time_pressure': 'Focus on time-critical tasks first',
            'many_dependencies': 'Plan for dependency management'
        }
        
        for factor in risk_factors:
            if factor in factor_recommendations:
                recommendations.append(factor_recommendations[factor])
        
        return recommendations
    
    def optimize_decision(self, agent_id: str, decisions: List[Dict], constraints: Dict = None) -> Dict:
        """Optimize a set of decisions"""
        # Simple optimization - prioritize high-scoring decisions
        optimized = sorted(decisions, key=lambda d: d.get('score', 0), reverse=True)
        
        # Apply constraints
        if constraints:
            max_decisions = constraints.get('max_decisions', len(optimized))
            optimized = optimized[:max_decisions]
        
        optimization_result = {
            'agent_id': agent_id,
            'original_count': len(decisions),
            'optimized_count': len(optimized),
            'optimized_decisions': optimized,
            'improvement': (optimized[0].get('score', 0) - decisions[0].get('score', 0)) if optimized and decisions else 0,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store optimization
        if agent_id not in self.intelligence['optimizations']:
            self.intelligence['optimizations'][agent_id] = []
        self.intelligence['optimizations'][agent_id].append(optimization_result)
        if len(self.intelligence['optimizations'][agent_id]) > 100:
            self.intelligence['optimizations'][agent_id] = self.intelligence['optimizations'][agent_id][-100:]
        
        self.save_intelligence()
        return optimization_result
    
    def understand_context(self, agent_id: str, context: Dict) -> Dict:
        """Understand and analyze context"""
        understanding = {
            'agent_id': agent_id,
            'context': self._serializable_copy(context),
            'key_factors': list(context.keys()) if isinstance(context, dict) else [],
            'complexity': len(context),
            'priority_elements': self._identify_priorities(context),
            'relationships': self._identify_relationships(context),
            'timestamp': datetime.now().isoformat()
        }
        
        # Store understanding
        if agent_id not in self.intelligence['context_understanding']:
            self.intelligence['context_understanding'][agent_id] = []
        self.intelligence['context_understanding'][agent_id].append(understanding)
        if len(self.intelligence['context_understanding'][agent_id]) > 100:
            self.intelligence['context_understanding'][agent_id] = self.intelligence['context_understanding'][agent_id][-100:]
        
        self.save_intelligence()
        return understanding
    
    def _identify_priorities(self, context: Dict) -> List[str]:
        """Identify priority elements in context"""
        # Simple priority identification
        priority_keywords = ['error', 'critical', 'important', 'urgent', 'priority']
        priorities = [k for k in context.keys() if any(keyword in k.lower() for keyword in priority_keywords)]
        return priorities[:5]
    
    def _identify_relationships(self, context: Dict) -> Dict:
        """Identify relationships between context elements"""
        # Simple relationship identification
        return {'count': len(context), 'types': list(set(type(v).__name__ for v in context.values()))}
    
    def get_agent_intelligence(self, agent_id: str) -> Dict:
        """Get intelligence data for an agent"""
        agent_data = self.intelligence['agents'].get(agent_id, {})
        predictions = self.intelligence['predictions'].get(agent_id, [])
        patterns = self.intelligence['patterns'].get(agent_id, [])
        strategies = self.intelligence['strategies'].get(agent_id, [])
        risk_assessments = self.intelligence['risk_assessments'].get(agent_id, [])
        optimizations = self.intelligence['optimizations'].get(agent_id, [])
        
        return {
            'agent_id': agent_id,
            'decisions_made': agent_data.get('decisions_made', 0),
            'successful_decisions': agent_data.get('successful_decisions', 0),
            'success_rate': (agent_data.get('successful_decisions', 0) / agent_data.get('decisions_made', 1)) * 100 if agent_data.get('decisions_made', 0) > 0 else 0,
            'predictions_count': len(predictions),
            'patterns_count': len(patterns),
            'strategies_count': len(strategies),
            'risk_assessments_count': len(risk_assessments),
            'optimizations_count': len(optimizations),
            'recent_predictions': predictions[-5:] if predictions else [],
            'recent_patterns': patterns[-5:] if patterns else [],
            'recent_strategies': strategies[-5:] if strategies else []
        }
    
    def get_all_intelligence(self) -> Dict:
        """Get all intelligence data"""
        return {
            'agents_count': len(self.intelligence['agents']),
            'total_decisions': len(self.intelligence['decisions']),
            'total_learning_entries': len(self.intelligence['learning_history']),
            'agents': {agent_id: self.get_agent_intelligence(agent_id) 
                      for agent_id in self.intelligence['agents'].keys()},
            'last_updated': self.intelligence.get('last_updated')
        }
    
    def get_tech_sector_intelligence(self, sector: str) -> Dict:
        """Get intelligence for a specific tech sector"""
        if sector not in self.intelligence['knowledge_base']:
            self.intelligence['knowledge_base'][sector] = {
                'sector': sector,
                'expertise_level': 0,
                'tasks_completed': 0,
                'success_rate': 0.0,
                'patterns': [],
                'strategies': [],
                'last_updated': datetime.now().isoformat()
            }
        
        return self.intelligence['knowledge_base'][sector]
    
    def update_tech_sector_intelligence(self, sector: str, task_result: Dict) -> Dict:
        """Update intelligence for a tech sector based on task completion"""
        sector_data = self.get_tech_sector_intelligence(sector)
        
        # Update statistics
        sector_data['tasks_completed'] = sector_data.get('tasks_completed', 0) + 1
        
        # Update success rate
        if task_result.get('success', False):
            current_success = sector_data.get('success_rate', 0.0)
            tasks = sector_data['tasks_completed']
            sector_data['success_rate'] = ((current_success * (tasks - 1)) + 1.0) / tasks
        else:
            current_success = sector_data.get('success_rate', 0.0)
            tasks = sector_data['tasks_completed']
            sector_data['success_rate'] = (current_success * (tasks - 1)) / tasks if tasks > 0 else 0.0
        
        # Update expertise level based on tasks completed
        sector_data['expertise_level'] = min(100, sector_data['tasks_completed'] * 2)
        
        # Store patterns
        if 'pattern' in task_result:
            if 'patterns' not in sector_data:
                sector_data['patterns'] = []
            sector_data['patterns'].append({
                'pattern': task_result['pattern'],
                'timestamp': datetime.now().isoformat(),
                'success': task_result.get('success', False)
            })
            if len(sector_data['patterns']) > 50:
                sector_data['patterns'] = sector_data['patterns'][-50:]
        
        sector_data['last_updated'] = datetime.now().isoformat()
        self.intelligence['knowledge_base'][sector] = sector_data
        self.save_intelligence()
        
        return sector_data
    
    def get_sector_recommendations(self, sector: str) -> List[str]:
        """Get recommendations for a tech sector based on intelligence"""
        sector_data = self.get_tech_sector_intelligence(sector)
        recommendations = []
        
        # Low success rate recommendation
        if sector_data.get('success_rate', 1.0) < 0.7:
            recommendations.append(f"Success rate is {sector_data['success_rate']*100:.1f}%. Consider reviewing failed tasks.")
        
        # Low expertise recommendation
        if sector_data.get('expertise_level', 0) < 50:
            recommendations.append(f"Expertise level is {sector_data['expertise_level']}. Complete more tasks to increase expertise.")
        
        # Pattern-based recommendations
        patterns = sector_data.get('patterns', [])
        if patterns:
            failed_patterns = [p for p in patterns if not p.get('success', True)]
            if len(failed_patterns) > len(patterns) * 0.3:
                recommendations.append("High failure rate detected. Review common failure patterns.")
        
        return recommendations
    
    def process_signal_from_collector(self, signal: Dict) -> Dict:
        """Process a signal from the signal collector and integrate into brain"""
        signal_id = signal.get('signal_id')
        source = signal.get('source')
        signal_type = signal.get('signal_type')
        data = signal.get('data', {})
        
        # Create intelligence entry from signal (serializable to avoid recursion on save)
        intelligence_entry = {
            'signal_id': signal_id,
            'source': source,
            'type': signal_type,
            'data': self._serializable_copy(data) if isinstance(data, (dict, list)) else data,
            'processed_at': datetime.now().isoformat(),
            'category': self._categorize_signal(signal_type, data)
        }
        
        # Store in knowledge base
        category = intelligence_entry['category']
        if category not in self.intelligence['knowledge_base']:
            self.intelligence['knowledge_base'][category] = {
                'signals': [],
                'patterns': [],
                'last_updated': datetime.now().isoformat()
            }
        
        self.intelligence['knowledge_base'][category]['signals'].append(intelligence_entry)
        
        # Keep only last 100 signals per category
        if len(self.intelligence['knowledge_base'][category]['signals']) > 100:
            self.intelligence['knowledge_base'][category]['signals'] = \
                self.intelligence['knowledge_base'][category]['signals'][-100:]
        
        self.save_intelligence()
        
        return intelligence_entry
    
    def _categorize_signal(self, signal_type: str, data: Dict) -> str:
        """Categorize a signal"""
        text = f"{signal_type} {json.dumps(data)}".lower()
        
        if any(kw in text for kw in ['youtube', 'video', 'media']):
            return 'media'
        elif any(kw in text for kw in ['music', 'audio', 'darksynth', 'synthwave', 'cyberpunk']):
            return 'music'
        elif any(kw in text for kw in ['invoke', 'command', 'action']):
            return 'command'
        elif any(kw in text for kw in ['error', 'warning', 'exception']):
            return 'error'
        elif any(kw in text for kw in ['path', 'route', 'url']):
            return 'routing'
        else:
            return 'general'

# Tech sectors configuration
TECH_SECTORS = {
    'frontend': {
        'name': 'Frontend Development',
        'technologies': ['React', 'Vue', 'Angular', 'HTML', 'CSS', 'JavaScript'],
        'common_tasks': ['debug_frontend', 'fix_ui_issues', 'optimize_performance']
    },
    'backend': {
        'name': 'Backend Development',
        'technologies': ['Python', 'Flask', 'SQLAlchemy', 'REST API'],
        'common_tasks': ['debug_route', 'fix_api_errors', 'optimize_database']
    },
    'database': {
        'name': 'Database Management',
        'technologies': ['SQLite', 'PostgreSQL', 'MySQL'],
        'common_tasks': ['verify_database', 'optimize_queries', 'migrate_schema']
    },
    'devops': {
        'name': 'DevOps & Infrastructure',
        'technologies': ['Docker', 'CI/CD', 'Monitoring'],
        'common_tasks': ['deploy_application', 'monitor_health', 'scale_resources']
    },
    'security': {
        'name': 'Security',
        'technologies': ['Authentication', 'Authorization', 'Encryption'],
        'common_tasks': ['scan_vulnerabilities', 'fix_security_issues', 'audit_access']
    },
    'testing': {
        'name': 'Testing & QA',
        'technologies': ['Unit Tests', 'Integration Tests', 'E2E Tests'],
        'common_tasks': ['run_tests', 'fix_test_failures', 'improve_coverage']
    }
}

# Global instance
agent_ai_intelligence = AgentAIIntelligence()

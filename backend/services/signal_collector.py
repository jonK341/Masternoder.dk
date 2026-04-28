"""
Signal Collector Service
Collects and pairs signals from various sources (YouTube, external APIs, system events)
and feeds them into the agent intelligence brain
"""
import os
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SignalCollector:
    """Signal collection system that feeds into agent intelligence brain"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.signals_file = os.path.join(self.base_dir, 'logs', 'signal_collector', 'signals.json')
        self.paired_signals_file = os.path.join(self.base_dir, 'logs', 'signal_collector', 'paired_signals.json')
        self.load_data()
    
    def load_data(self):
        """Load signal data"""
        os.makedirs(os.path.dirname(self.signals_file), exist_ok=True)
        
        if os.path.exists(self.signals_file):
            try:
                with open(self.signals_file, 'r') as f:
                    self.signals = json.load(f)
            except:
                self.signals = self._default_signals()
        else:
            self.signals = self._default_signals()
        
        if os.path.exists(self.paired_signals_file):
            try:
                with open(self.paired_signals_file, 'r') as f:
                    self.paired_signals = json.load(f)
            except:
                self.paired_signals = {}
        else:
            self.paired_signals = {}
        
        self.save_data()
    
    def _default_signals(self) -> Dict:
        """Default signals structure"""
        return {
            'signals': [],
            'sources': {},
            'categories': {},
            'last_updated': datetime.now().isoformat()
        }
    
    def save_data(self):
        """Save signal data"""
        try:
            self.signals['last_updated'] = datetime.now().isoformat()
            with open(self.signals_file, 'w') as f:
                json.dump(self.signals, f, indent=2, default=str)
            with open(self.paired_signals_file, 'w') as f:
                json.dump(self.paired_signals, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving signal data: {e}")
    
    def collect_signal(self, source: str, signal_type: str, data: Dict, 
                      metadata: Optional[Dict] = None) -> Dict:
        """Collect a signal from a source"""
        signal_id = f"signal_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        signal = {
            'signal_id': signal_id,
            'source': source,
            'signal_type': signal_type,
            'data': data,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat(),
            'processed': False,
            'paired': False
        }
        
        # Add to signals list
        if 'signals' not in self.signals:
            self.signals['signals'] = []
        self.signals['signals'].append(signal)
        
        # Track by source
        if source not in self.signals['sources']:
            self.signals['sources'][source] = {
                'count': 0,
                'types': {},
                'last_signal': None
            }
        self.signals['sources'][source]['count'] += 1
        self.signals['sources'][source]['last_signal'] = signal_id
        
        if signal_type not in self.signals['sources'][source]['types']:
            self.signals['sources'][source]['types'][signal_type] = 0
        self.signals['sources'][source]['types'][signal_type] += 1
        
        # Track by category
        category = self._extract_category(signal_type, data)
        if category not in self.signals['categories']:
            self.signals['categories'][category] = {
                'count': 0,
                'signals': []
            }
        self.signals['categories'][category]['count'] += 1
        self.signals['categories'][category]['signals'].append(signal_id)
        
        # Keep only last 1000 signals
        if len(self.signals['signals']) > 1000:
            self.signals['signals'] = self.signals['signals'][-1000:]
        
        self.save_data()
        
        # Try to pair with existing signals
        paired = self._try_pair_signal(signal)
        if paired:
            signal['paired'] = True
            self._feed_to_brain(signal, paired)
        
        # Use AI to process signal intelligently
        try:
            from backend.services.ai_enhanced_signals import ai_enhanced_signals
            ai_result = ai_enhanced_signals.intelligent_signal_processing(signal)
            signal['ai_processed'] = True
            signal['ai_recommendation'] = ai_result.get('ai_recommendation', 'store')
        except Exception as e:
            print(f"Error in AI signal processing: {e}")
        
        return signal
    
    def _extract_category(self, signal_type: str, data: Dict) -> str:
        """Extract category from signal"""
        # Extract keywords from signal type and data
        text = f"{signal_type} {json.dumps(data)}".lower()
        
        categories = {
            'music': ['darksynth', 'synthwave', 'cyberpunk', 'music', 'audio', 'youtube'],
            'media': ['video', 'youtube', 'stream', 'content'],
            'system': ['error', 'warning', 'event', 'log'],
            'user': ['user', 'action', 'click', 'interaction'],
            'api': ['api', 'endpoint', 'request', 'response'],
            'agent': ['agent', 'task', 'mission', 'intelligence']
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return 'general'
    
    def _try_pair_signal(self, signal: Dict) -> Optional[Dict]:
        """Try to pair a signal with existing signals"""
        signal_type = signal['signal_type']
        data = signal['data']
        source = signal['source']
        
        # Look for similar signals
        for existing_signal in self.signals['signals'][-100:]:  # Check last 100
            if existing_signal['signal_id'] == signal['signal_id']:
                continue
            
            # Check if signals can be paired
            if self._signals_match(signal, existing_signal):
                pair_id = f"pair_{signal['signal_id']}_{existing_signal['signal_id']}"
                
                paired_signal = {
                    'pair_id': pair_id,
                    'signal1': signal,
                    'signal2': existing_signal,
                    'paired_at': datetime.now().isoformat(),
                    'confidence': self._calculate_pair_confidence(signal, existing_signal),
                    'category': self._extract_category(signal_type, data)
                }
                
                if pair_id not in self.paired_signals:
                    self.paired_signals[pair_id] = paired_signal
                    signal['paired'] = True
                    existing_signal['paired'] = True
                    self.save_data()
                    return paired_signal
        
        return None
    
    def _signals_match(self, signal1: Dict, signal2: Dict) -> bool:
        """Check if two signals match for pairing"""
        # Same source and similar type
        if signal1['source'] == signal2['source']:
            if signal1['signal_type'] == signal2['signal_type']:
                return True
        
        # Similar keywords in data
        data1_text = json.dumps(signal1['data']).lower()
        data2_text = json.dumps(signal2['data']).lower()
        
        # Extract keywords
        keywords1 = set(re.findall(r'\b\w{4,}\b', data1_text))
        keywords2 = set(re.findall(r'\b\w{4,}\b', data2_text))
        
        # If significant overlap
        if len(keywords1 & keywords2) >= 3:
            return True
        
        # Time proximity (within 5 minutes)
        try:
            time1 = datetime.fromisoformat(signal1['timestamp'])
            time2 = datetime.fromisoformat(signal2['timestamp'])
            time_diff = abs((time1 - time2).total_seconds())
            if time_diff < 300 and len(keywords1 & keywords2) >= 2:
                return True
        except:
            pass
        
        return False
    
    def _calculate_pair_confidence(self, signal1: Dict, signal2: Dict) -> float:
        """Calculate confidence score for signal pairing"""
        confidence = 0.0
        
        # Same source: +0.3
        if signal1['source'] == signal2['source']:
            confidence += 0.3
        
        # Same type: +0.3
        if signal1['signal_type'] == signal2['signal_type']:
            confidence += 0.3
        
        # Keyword overlap: +0.4
        data1_text = json.dumps(signal1['data']).lower()
        data2_text = json.dumps(signal2['data']).lower()
        keywords1 = set(re.findall(r'\b\w{4,}\b', data1_text))
        keywords2 = set(re.findall(r'\b\w{4,}\b', data2_text))
        overlap = len(keywords1 & keywords2)
        total = len(keywords1 | keywords2)
        if total > 0:
            confidence += (overlap / total) * 0.4
        
        return min(1.0, confidence)
    
    def _feed_to_brain(self, signal: Dict, paired_signal: Optional[Dict] = None):
        """Feed signal to agent intelligence brain"""
        try:
            from backend.services.agent_ai_intelligence import agent_ai_intelligence
            
            # Create context from signal
            context = {
                'signal_id': signal['signal_id'],
                'source': signal['source'],
                'signal_type': signal['signal_type'],
                'category': self._extract_category(signal['signal_type'], signal['data']),
                'data': signal['data'],
                'timestamp': signal['timestamp']
            }
            
            if paired_signal:
                context['paired'] = True
                context['pair_id'] = paired_signal['pair_id']
                context['confidence'] = paired_signal['confidence']
            
            # Feed to brain as learning experience
            agent_ai_intelligence.learn_from_experience(
                agent_id='signal_collector',
                experience={
                    'action': 'signal_collected',
                    'context': context,
                    'outcome': 'success' if paired_signal else 'neutral'
                }
            )
            
            # Update knowledge base with signal patterns
            category = context['category']
            if category not in agent_ai_intelligence.intelligence['knowledge_base']:
                agent_ai_intelligence.intelligence['knowledge_base'][category] = {
                    'signals': [],
                    'patterns': [],
                    'last_updated': datetime.now().isoformat()
                }
            
            agent_ai_intelligence.intelligence['knowledge_base'][category]['signals'].append({
                'signal_id': signal['signal_id'],
                'source': signal['source'],
                'type': signal['signal_type'],
                'timestamp': signal['timestamp']
            })
            
            # Keep only last 100 signals per category
            if len(agent_ai_intelligence.intelligence['knowledge_base'][category]['signals']) > 100:
                agent_ai_intelligence.intelligence['knowledge_base'][category]['signals'] = \
                    agent_ai_intelligence.intelligence['knowledge_base'][category]['signals'][-100:]
            
            agent_ai_intelligence.save_intelligence()
            
        except Exception as e:
            print(f"Error feeding signal to brain: {e}")
    
    def process_invoke_message(self, message: str) -> Dict:
        """Process INVOKE messages (e.g., 'INVOKE - darksynth / synthwave / cyberpunk / from youtube')"""
        # Parse INVOKE message
        parts = message.replace('INVOKE', '').strip().split('/')
        keywords = [p.strip() for p in parts if p.strip()]
        
        signal_data = {
            'message': message,
            'keywords': keywords,
            'source': 'invoke',
            'parsed': True
        }
        
        # Determine signal type
        signal_type = 'invoke_request'
        if 'youtube' in message.lower():
            signal_type = 'youtube_invoke'
        
        # Collect signal
        signal = self.collect_signal(
            source='invoke',
            signal_type=signal_type,
            data=signal_data,
            metadata={
                'original_message': message,
                'parsed_keywords': keywords
            }
        )
        
        return signal
    
    def get_signals(self, source: Optional[str] = None, category: Optional[str] = None,
                   limit: int = 100) -> List[Dict]:
        """Get collected signals"""
        signals = self.signals.get('signals', [])
        
        if source:
            signals = [s for s in signals if s.get('source') == source]
        
        if category:
            signals = [s for s in signals if self._extract_category(s.get('signal_type', ''), s.get('data', {})) == category]
        
        return signals[-limit:]
    
    def get_paired_signals(self, limit: int = 50) -> List[Dict]:
        """Get paired signals"""
        pairs = list(self.paired_signals.values())
        return sorted(pairs, key=lambda x: x.get('paired_at', ''), reverse=True)[:limit]


# Global instance
signal_collector = SignalCollector()

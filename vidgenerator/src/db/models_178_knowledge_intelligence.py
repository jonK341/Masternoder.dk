"""
178 Point Systems Knowledge & Intelligence Tables
Adds knowledge and intelligence context to all 178 point systems
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.sql import func
import json

# Import existing db instance
from src.db.models import db


class PointSystemKnowledge(db.Model):
    """
    Knowledge table for 178 point systems
    Stores knowledge, context, and information about each system
    """
    __tablename__ = 'point_system_knowledge'
    
    id = db.Column(db.String(36), primary_key=True)
    system_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    
    # Knowledge Content
    system_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    detailed_description = db.Column(db.Text)  # Comprehensive description
    context = db.Column(db.Text)  # Context and use cases
    examples = db.Column(db.Text)  # JSON: examples of usage
    best_practices = db.Column(db.Text)  # JSON: best practices
    strategies = db.Column(db.Text)  # JSON: optimization strategies
    
    # Intelligence Data
    intelligence_score = db.Column(db.Float, default=0.0)  # AI intelligence score
    complexity_level = db.Column(db.Integer, default=1)  # 1-10 complexity
    learning_curve = db.Column(db.String(50), default='easy')  # easy, medium, hard, expert
    mastery_requirements = db.Column(db.Text)  # JSON: requirements for mastery
    
    # Relationships
    related_systems = db.Column(db.Text)  # JSON: related system IDs
    prerequisites = db.Column(db.Text)  # JSON: prerequisite systems
    unlocks = db.Column(db.Text)  # JSON: systems this unlocks
    
    # Knowledge Points
    knowledge_points_value = db.Column(db.Integer, default=0)  # Knowledge points earned
    intelligence_points_value = db.Column(db.Integer, default=0)  # Intelligence points earned
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'system_id': self.system_id,
            'system_name': self.system_name,
            'description': self.description,
            'detailed_description': self.detailed_description,
            'context': self.context,
            'examples': json.loads(self.examples) if self.examples else [],
            'best_practices': json.loads(self.best_practices) if self.best_practices else [],
            'strategies': json.loads(self.strategies) if self.strategies else [],
            'intelligence_score': self.intelligence_score,
            'complexity_level': self.complexity_level,
            'learning_curve': self.learning_curve,
            'mastery_requirements': json.loads(self.mastery_requirements) if self.mastery_requirements else {},
            'related_systems': json.loads(self.related_systems) if self.related_systems else [],
            'prerequisites': json.loads(self.prerequisites) if self.prerequisites else [],
            'unlocks': json.loads(self.unlocks) if self.unlocks else [],
            'knowledge_points_value': self.knowledge_points_value,
            'intelligence_points_value': self.intelligence_points_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PointSystemIntelligence(db.Model):
    """
    Intelligence table for 178 point systems
    Stores AI intelligence data, calculations, and insights
    """
    __tablename__ = 'point_system_intelligence'
    
    id = db.Column(db.String(36), primary_key=True)
    system_id = db.Column(db.String(100), nullable=False, index=True)
    user_id = db.Column(db.String(100), nullable=False, index=True)
    
    # Intelligence Metrics
    intelligence_score = db.Column(db.Float, default=0.0)  # Overall intelligence score
    calculation_accuracy = db.Column(db.Float, default=0.0)  # Calculation accuracy
    prediction_accuracy = db.Column(db.Float, default=0.0)  # Prediction accuracy
    pattern_recognition_score = db.Column(db.Float, default=0.0)  # Pattern recognition
    
    # AI Analysis
    ai_insights = db.Column(db.Text)  # JSON: AI-generated insights
    recommendations = db.Column(db.Text)  # JSON: AI recommendations
    optimizations = db.Column(db.Text)  # JSON: optimization suggestions
    
    # Neural Network Data
    neural_analysis = db.Column(db.Text)  # JSON: neural network analysis
    learning_data = db.Column(db.Text)  # JSON: machine learning data
    
    # Quantum Calculations
    quantum_state = db.Column(db.Text)  # JSON: quantum calculation state
    multi_dimensional_data = db.Column(db.Text)  # JSON: multi-dimensional calculations
    
    # Statistics
    total_calculations = db.Column(db.Integer, default=0)
    successful_calculations = db.Column(db.Integer, default=0)
    failed_calculations = db.Column(db.Integer, default=0)
    average_confidence = db.Column(db.Float, default=0.0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'system_id': self.system_id,
            'user_id': self.user_id,
            'intelligence_score': self.intelligence_score,
            'calculation_accuracy': self.calculation_accuracy,
            'prediction_accuracy': self.prediction_accuracy,
            'pattern_recognition_score': self.pattern_recognition_score,
            'ai_insights': json.loads(self.ai_insights) if self.ai_insights else [],
            'recommendations': json.loads(self.recommendations) if self.recommendations else [],
            'optimizations': json.loads(self.optimizations) if self.optimizations else [],
            'neural_analysis': json.loads(self.neural_analysis) if self.neural_analysis else {},
            'learning_data': json.loads(self.learning_data) if self.learning_data else {},
            'quantum_state': json.loads(self.quantum_state) if self.quantum_state else {},
            'multi_dimensional_data': json.loads(self.multi_dimensional_data) if self.multi_dimensional_data else {},
            'total_calculations': self.total_calculations,
            'successful_calculations': self.successful_calculations,
            'failed_calculations': self.failed_calculations,
            'average_confidence': self.average_confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


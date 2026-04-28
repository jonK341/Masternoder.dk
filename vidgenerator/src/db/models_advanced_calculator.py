"""
Database Models for Advanced Intelligent Calculator
Stores calculation history, point loss detection, repairs, predictions, and pattern analysis
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship

# Use Flask-SQLAlchemy's db from main app (same metadata for extend_existing)
try:
    from src.db.models import db
    Base = db.Model
except ImportError:
    try:
        from vidgenerator.src.db.models import db
        Base = db.Model
    except ImportError:
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()


class CalculationHistory(Base):
    """Stores history of all intelligent calculations"""
    __tablename__ = 'calculation_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    calculation_type = Column(String(50), nullable=False)  # 'intelligent', 'atomic', 'financial', etc.
    
    # Calculation results
    final_total = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=False, default=0.0)
    points_restored = Column(Float, nullable=False, default=0.0)
    anomalies_detected_count = Column(Integer, nullable=False, default=0)
    
    # Detailed calculation data (JSON)
    calculation_data = Column(JSON, nullable=True)  # Full calculation breakdown
    system_breakdown = Column(JSON, nullable=True)  # Points per system
    multipliers_applied = Column(JSON, nullable=True)  # Applied multipliers
    insights = Column(JSON, nullable=True)  # Generated insights
    
    # Metadata
    calculation_duration_ms = Column(Integer, nullable=True)  # Time taken in milliseconds
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    anomalies = relationship("AnomalyDetection", back_populates="calculation", cascade="all, delete-orphan")
    repairs = relationship("RepairLog", back_populates="calculation", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_user_calc_type', 'user_id', 'calculation_type'),
        Index('idx_user_created', 'user_id', 'created_at'),
        {'extend_existing': True},
    )


class PointLossDetection(Base):
    """Stores point loss detection records"""
    __tablename__ = 'point_loss_detection'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    
    # Detection results
    points_lost = Column(Float, nullable=False, default=0.0)
    systems_affected = Column(Integer, nullable=False, default=0)
    detection_confidence = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    
    # Detailed detection data
    affected_systems = Column(JSON, nullable=True)  # List of systems with losses
    loss_breakdown = Column(JSON, nullable=True)  # Detailed loss per system
    detection_method = Column(String(50), nullable=True)  # 'statistical', 'pattern', 'neural', etc.
    
    # Status
    is_resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    repairs = relationship("RepairLog", back_populates="loss_detection", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_user_resolved', 'user_id', 'is_resolved'),
        Index('idx_user_created_loss', 'user_id', 'created_at'),
        {'extend_existing': True},
    )


class RepairLog(Base):
    """Stores repair operations performed by the calculator"""
    __tablename__ = 'repair_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    
    # Foreign keys
    calculation_id = Column(Integer, ForeignKey('calculation_history.id'), nullable=True)
    loss_detection_id = Column(Integer, ForeignKey('point_loss_detection.id'), nullable=True)
    
    # Repair details
    repair_type = Column(String(50), nullable=False)  # 'point_restoration', 'anomaly_fix', 'system_repair', etc.
    systems_checked = Column(Integer, nullable=False, default=0)
    issues_detected = Column(Integer, nullable=False, default=0)
    points_restored = Column(Float, nullable=False, default=0.0)
    
    # Detailed repair data
    repairs_performed = Column(JSON, nullable=True)  # List of repairs
    issues_found = Column(JSON, nullable=True)  # List of issues detected
    systems_repaired = Column(JSON, nullable=True)  # Systems that were repaired
    
    # Status
    success = Column(Boolean, default=False, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    repair_duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    calculation = relationship("CalculationHistory", back_populates="repairs")
    loss_detection = relationship("PointLossDetection", back_populates="repairs")
    
    __table_args__ = (
        Index('idx_user_success', 'user_id', 'success'),
        Index('idx_user_created_repair', 'user_id', 'created_at'),
        {'extend_existing': True},
    )


class Prediction(Base):
    """Stores future point predictions"""
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    
    # Prediction parameters
    prediction_type = Column(String(50), nullable=False)  # 'future_points', 'trend', 'correction', etc.
    days_ahead = Column(Integer, nullable=False, default=30)
    
    # Prediction results
    predicted_points = Column(Float, nullable=False, default=0.0)
    confidence_level = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    prediction_range_min = Column(Float, nullable=True)  # Lower bound
    prediction_range_max = Column(Float, nullable=True)  # Upper bound
    
    # Detailed prediction data
    prediction_breakdown = Column(JSON, nullable=True)  # Points per system prediction
    factors_considered = Column(JSON, nullable=True)  # Factors used in prediction
    historical_data_points = Column(Integer, nullable=True)  # Number of data points used
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        Index('idx_user_type', 'user_id', 'prediction_type'),
        Index('idx_user_created_pred', 'user_id', 'created_at'),
        {'extend_existing': True},
    )


class PatternAnalysis(Base):
    """Stores pattern analysis results"""
    __tablename__ = 'pattern_analysis'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    
    # Analysis results
    analysis_type = Column(String(50), nullable=False)  # 'trend', 'anomaly', 'correlation', 'neural', etc.
    patterns_found = Column(Integer, nullable=False, default=0)
    confidence_score = Column(Float, nullable=False, default=0.0)
    
    # Detailed analysis data
    patterns = Column(JSON, nullable=True)  # List of detected patterns
    insights = Column(JSON, nullable=True)  # Generated insights
    recommendations = Column(JSON, nullable=True)  # Recommendations based on patterns
    
    # Analysis parameters
    data_range_days = Column(Integer, nullable=True)  # Days of data analyzed
    systems_analyzed = Column(JSON, nullable=True)  # Systems included in analysis
    
    # Metadata
    analysis_duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        Index('idx_user_type_analysis', 'user_id', 'analysis_type'),
        Index('idx_user_created_analysis', 'user_id', 'created_at'),
        {'extend_existing': True},
    )


class AnomalyDetection(Base):
    """Stores anomaly detection records"""
    __tablename__ = 'anomaly_detection'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    
    # Foreign key
    calculation_id = Column(Integer, ForeignKey('calculation_history.id'), nullable=True)
    
    # Anomaly details
    anomaly_type = Column(String(50), nullable=False)  # 'statistical', 'pattern', 'neural', etc.
    severity = Column(String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'
    confidence = Column(Float, nullable=False, default=0.0)
    
    # Anomaly data
    affected_system = Column(String(100), nullable=True)  # Which system has the anomaly
    expected_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    deviation = Column(Float, nullable=True)  # Difference between expected and actual
    
    # Detailed anomaly information
    anomaly_details = Column(JSON, nullable=True)  # Additional details
    suggested_fix = Column(JSON, nullable=True)  # Suggested fix actions
    
    # Status
    is_fixed = Column(Boolean, default=False, nullable=False, index=True)
    fixed_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    calculation = relationship("CalculationHistory", back_populates="anomalies")
    
    __table_args__ = (
        Index('idx_user_fixed', 'user_id', 'is_fixed'),
        Index('idx_user_severity', 'user_id', 'severity'),
        Index('idx_user_created_anomaly', 'user_id', 'created_at'),
        {'extend_existing': True},
    )


class SystemPointSnapshot(Base):
    """Stores snapshots of system points at calculation time"""
    __tablename__ = 'system_point_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    calculation_id = Column(Integer, ForeignKey('calculation_history.id'), nullable=True)
    
    # Snapshot data
    system_name = Column(String(100), nullable=False)
    point_value = Column(Float, nullable=False, default=0.0)
    multiplier_applied = Column(Float, nullable=True, default=1.0)
    calculated_total = Column(Float, nullable=False, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        Index('idx_user_system', 'user_id', 'system_name'),
        Index('idx_calc_system', 'calculation_id', 'system_name'),
        {'extend_existing': True},
    )

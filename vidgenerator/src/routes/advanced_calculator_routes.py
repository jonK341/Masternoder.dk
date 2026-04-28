"""
API Routes for Advanced Intelligent Calculator
"""
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import Session

try:
    from vidgenerator.src.services.advanced_intelligent_calculator import AdvancedIntelligentCalculator
except ImportError:
    from src.services.advanced_intelligent_calculator import AdvancedIntelligentCalculator

# Create blueprint
advanced_calculator_bp = Blueprint('advanced_calculator', __name__)


def get_db_session():
    """Get database session from Flask-SQLAlchemy"""
    try:
        from src.db.models import db
        return db.session
    except ImportError:
        # Fallback: try to get from app context
        if hasattr(current_app, 'extensions') and 'sqlalchemy' in current_app.extensions:
            return current_app.extensions['sqlalchemy'].db.session
        raise Exception("Database session not available")


@advanced_calculator_bp.route('/api/advanced-calculator/calculate', methods=['POST'])
def calculate_with_intelligence():
    """Calculate points with intelligence"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        
        db_session = get_db_session()
        calculator = AdvancedIntelligentCalculator(db_session)
        result = calculator.calculate_with_intelligence(user_id)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@advanced_calculator_bp.route('/api/advanced-calculator/detect-loss/<user_id>', methods=['GET'])
def detect_point_loss(user_id):
    """Detect point losses"""
    try:
        db_session = get_db_session()
        calculator = AdvancedIntelligentCalculator(db_session)
        result = calculator.detect_point_loss(user_id)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@advanced_calculator_bp.route('/api/advanced-calculator/repair-all/<user_id>', methods=['POST'])
def repair_all_systems(user_id):
    """Repair all systems"""
    try:
        db_session = get_db_session()
        calculator = AdvancedIntelligentCalculator(db_session)
        result = calculator.repair_all_systems(user_id)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@advanced_calculator_bp.route('/api/advanced-calculator/comprehensive-repair/<user_id>', methods=['POST'])
def comprehensive_repair(user_id):
    """Comprehensive repair"""
    try:
        db_session = get_db_session()
        calculator = AdvancedIntelligentCalculator(db_session)
        result = calculator.comprehensive_repair(user_id)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@advanced_calculator_bp.route('/api/advanced-calculator/predict/<user_id>', methods=['GET'])
def predict_future(user_id):
    """Predict future points"""
    try:
        days = request.args.get('days', 30, type=int)
        
        db_session = get_db_session()
        calculator = AdvancedIntelligentCalculator(db_session)
        result = calculator.predict_future_points(user_id, days)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@advanced_calculator_bp.route('/api/advanced-calculator/analyze-patterns/<user_id>', methods=['GET'])
def analyze_patterns(user_id):
    """Analyze patterns"""
    try:
        db_session = get_db_session()
        calculator = AdvancedIntelligentCalculator(db_session)
        result = calculator.analyze_patterns(user_id)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@advanced_calculator_bp.route('/api/advanced-calculator/statistics/<user_id>', methods=['GET'])
def get_statistics(user_id):
    """Get comprehensive statistics"""
    try:
        days = request.args.get('days', 30, type=int)
        
        db_session = get_db_session()
        calculator = AdvancedIntelligentCalculator(db_session)
        result = calculator.get_comprehensive_statistics(user_id, days)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Atomic Calculator Routes
@advanced_calculator_bp.route('/api/atomic-calculator/calculate', methods=['POST'])
def atomic_calculate():
    """Atomic Calculator - Hell & Money Satan"""
    try:
        data = request.get_json() or {}
        base_value = float(data.get('base_value', 1000))
        calculation_type = data.get('calculation_type', 'hell_money')
        params = data.get('params', {})
        
        db_session = get_db_session()
        calculator = AdvancedIntelligentCalculator(db_session)
        result = calculator.atomic_calculate(base_value, calculation_type, params)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@advanced_calculator_bp.route('/api/atomic-calculator/financial-metrics', methods=['POST'])
def calculate_financial_metrics():
    """Calculate Financial Metrics"""
    try:
        data = request.get_json() or {}
        base_value = float(data.get('base_value', 1000))
        metrics = data.get('metrics', ['hell_money', 'satan_compound', 'atomic_interest'])
        
        db_session = get_db_session()
        calculator = AdvancedIntelligentCalculator(db_session)
        result = calculator.calculate_financial_metrics(base_value, metrics)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@advanced_calculator_bp.route('/api/atomic-calculator/money-satan-returns', methods=['POST'])
def calculate_money_satan_returns():
    """Calculate Money Satan Returns"""
    try:
        data = request.get_json() or {}
        investment = float(data.get('investment', 1000))
        time_periods = int(data.get('time_periods', 1))
        
        db_session = get_db_session()
        calculator = AdvancedIntelligentCalculator(db_session)
        result = calculator.calculate_money_satan_returns(investment, time_periods)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

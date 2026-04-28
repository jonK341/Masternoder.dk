"""
Error Logging API Routes
Handles error logging from frontend and provides error management endpoints
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from sqlalchemy.exc import SQLAlchemyError

from src.db.models import db
from src.db.models_error_logging import ErrorLog, ErrorSummary

error_logging_bp = Blueprint('error_logging', __name__)


def _empty_error_stats(days: int):
    return {
        'success': True,
        'period_days': days,
        'total_errors': 0,
        'unresolved_errors': 0,
        'errors_by_level': {},
        'errors_by_type': {},
        'top_error_groups': [],
        'top_pages': []
    }


def _empty_error_list(limit: int, offset: int):
    return {
        'success': True,
        'total': 0,
        'limit': limit,
        'offset': offset,
        'errors': []
    }


def _ensure_error_logging_tables():
    """Create error logging tables if they do not exist yet."""
    ErrorLog.__table__.create(bind=db.engine, checkfirst=True)
    ErrorSummary.__table__.create(bind=db.engine, checkfirst=True)


def _is_missing_table_error(exc: Exception) -> bool:
    """Detect missing table errors across sqlite/sqlalchemy variants."""
    message = str(exc).lower()
    return 'no such table' in message or 'does not exist' in message


@error_logging_bp.route('/api/errors/log', methods=['POST'])
def log_error():
    """
    Log an error from frontend or backend
    
    Expected JSON:
    {
        "error_type": "javascript|api|network|database",
        "error_level": "error|warning|critical|info",
        "error_code": "404|500|etc",
        "error_message": "Error message",
        "error_stack": "Stack trace",
        "error_source": "file.js:123",
        "error_line": 123,
        "error_column": 45,
        "page_url": "/vidgenerator/game",
        "context_data": {},
        "tags": ["api", "points"]
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        # Extract error data
        error_log = ErrorLog(
            error_type=data.get('error_type', 'unknown'),
            error_level=data.get('error_level', 'error'),
            error_code=data.get('error_code'),
            error_message=data.get('error_message', 'Unknown error'),
            error_stack=data.get('error_stack'),
            error_source=data.get('error_source'),
            error_line=data.get('error_line'),
            error_column=data.get('error_column'),
            user_id=data.get('user_id'),
            session_id=data.get('session_id'),
            page_url=data.get('page_url'),
            user_agent=request.headers.get('User-Agent'),
            request_method=data.get('request_method'),
            request_url=data.get('request_url'),
            request_headers=data.get('request_headers'),
            request_body=data.get('request_body'),
            response_status=data.get('response_status'),
            response_body=data.get('response_body'),
            context_data=data.get('context_data'),
            tags=data.get('tags', [])
        )
        
        # Try to group similar errors
        if error_log.error_message and error_log.error_source:
            # Find similar errors in last 24 hours
            similar_error = ErrorLog.query.filter(
                ErrorLog.error_message == error_log.error_message,
                ErrorLog.error_source == error_log.error_source,
                ErrorLog.created_at >= datetime.utcnow() - timedelta(hours=24),
                ErrorLog.is_resolved == False
            ).first()
            
            if similar_error:
                # Group with existing error
                error_log.error_group = similar_error.error_group or f"group_{similar_error.id}"
                similar_error.occurrence_count += 1
                db.session.add(similar_error)
            else:
                # Create new group
                error_log.error_group = f"group_{error_log.id}"
        
        db.session.add(error_log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'error_id': error_log.id,
            'error_group': error_log.error_group
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        if _is_missing_table_error(e):
            try:
                _ensure_error_logging_tables()
                data = request.get_json(silent=True) or {}
                error_log = ErrorLog(
                    error_type=data.get('error_type', 'unknown'),
                    error_level=data.get('error_level', 'error'),
                    error_code=data.get('error_code'),
                    error_message=data.get('error_message', 'Unknown error'),
                    error_stack=data.get('error_stack'),
                    error_source=data.get('error_source'),
                    error_line=data.get('error_line'),
                    error_column=data.get('error_column'),
                    user_id=data.get('user_id'),
                    session_id=data.get('session_id'),
                    page_url=data.get('page_url'),
                    user_agent=request.headers.get('User-Agent'),
                    request_method=data.get('request_method'),
                    request_url=data.get('request_url'),
                    request_headers=data.get('request_headers'),
                    request_body=data.get('request_body'),
                    response_status=data.get('response_status'),
                    response_body=data.get('response_body'),
                    context_data=data.get('context_data'),
                    tags=data.get('tags', [])
                )
                db.session.add(error_log)
                db.session.commit()
                return jsonify({
                    'success': True,
                    'error_id': error_log.id,
                    'error_group': error_log.error_group
                }), 201
            except Exception:
                db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to log error',
            'message': str(e)
        }), 500


@error_logging_bp.route('/api/errors/list', methods=['GET'])
def list_errors():
    """
    List errors with filtering and pagination
    
    Query parameters:
    - limit: Number of errors to return (default: 50)
    - offset: Offset for pagination (default: 0)
    - error_type: Filter by error type
    - error_level: Filter by error level
    - is_resolved: Filter by resolved status (true/false)
    - user_id: Filter by user ID
    - page_url: Filter by page URL
    - start_date: Start date (ISO format)
    - end_date: End date (ISO format)
    """
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    try:
        query = ErrorLog.query
        
        # Apply filters
        if request.args.get('error_type'):
            query = query.filter(ErrorLog.error_type == request.args.get('error_type'))
        
        if request.args.get('error_level'):
            query = query.filter(ErrorLog.error_level == request.args.get('error_level'))
        
        if request.args.get('is_resolved') is not None:
            is_resolved = request.args.get('is_resolved').lower() == 'true'
            query = query.filter(ErrorLog.is_resolved == is_resolved)
        
        if request.args.get('user_id'):
            query = query.filter(ErrorLog.user_id == request.args.get('user_id'))
        
        if request.args.get('page_url'):
            query = query.filter(ErrorLog.page_url.like(f"%{request.args.get('page_url')}%"))
        
        if request.args.get('start_date'):
            start_date = datetime.fromisoformat(request.args.get('start_date'))
            query = query.filter(ErrorLog.created_at >= start_date)
        
        if request.args.get('end_date'):
            end_date = datetime.fromisoformat(request.args.get('end_date'))
            query = query.filter(ErrorLog.created_at <= end_date)
        
        # Order by most recent first
        query = query.order_by(desc(ErrorLog.created_at))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        errors = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'success': True,
            'total': total,
            'limit': limit,
            'offset': offset,
            'errors': [error.to_dict() for error in errors]
        }), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        if _is_missing_table_error(e):
            try:
                _ensure_error_logging_tables()
                return jsonify(_empty_error_list(limit, offset)), 200
            except Exception:
                return jsonify(_empty_error_list(limit, offset)), 200
        return jsonify({
            'success': False,
            'error': 'Failed to list errors',
            'message': str(e)
        }), 500
    except Exception as e:
        # Safe fallback keeps dashboard usable during partial DB migration.
        if _is_missing_table_error(e):
            return jsonify(_empty_error_list(limit, offset)), 200
        return jsonify({
            'success': False,
            'error': 'Failed to list errors',
            'message': str(e)
        }), 500


@error_logging_bp.route('/api/errors/stats', methods=['GET'])
def error_stats():
    """
    Get error statistics
    
    Query parameters:
    - days: Number of days to include (default: 7)
    """
    days = int(request.args.get('days', 7))
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Total errors
        total_errors = ErrorLog.query.filter(
            ErrorLog.created_at >= start_date
        ).count()
        
        # Errors by level
        errors_by_level = db.session.query(
            ErrorLog.error_level,
            func.count(ErrorLog.id).label('count')
        ).filter(
            ErrorLog.created_at >= start_date
        ).group_by(ErrorLog.error_level).all()
        
        # Errors by type
        errors_by_type = db.session.query(
            ErrorLog.error_type,
            func.count(ErrorLog.id).label('count')
        ).filter(
            ErrorLog.created_at >= start_date
        ).group_by(ErrorLog.error_type).all()
        
        # Unresolved errors
        unresolved = ErrorLog.query.filter(
            ErrorLog.is_resolved == False,
            ErrorLog.created_at >= start_date
        ).count()
        
        # Top error groups
        top_groups = db.session.query(
            ErrorLog.error_group,
            ErrorLog.error_message,
            func.count(ErrorLog.id).label('count'),
            func.max(ErrorLog.created_at).label('last_occurrence')
        ).filter(
            ErrorLog.created_at >= start_date,
            ErrorLog.error_group.isnot(None)
        ).group_by(
            ErrorLog.error_group,
            ErrorLog.error_message
        ).order_by(desc('count')).limit(10).all()
        
        # Top pages with errors
        top_pages = db.session.query(
            ErrorLog.page_url,
            func.count(ErrorLog.id).label('count')
        ).filter(
            ErrorLog.created_at >= start_date,
            ErrorLog.page_url.isnot(None)
        ).group_by(ErrorLog.page_url).order_by(desc('count')).limit(10).all()
        
        return jsonify({
            'success': True,
            'period_days': days,
            'total_errors': total_errors,
            'unresolved_errors': unresolved,
            'errors_by_level': {level: count for level, count in errors_by_level},
            'errors_by_type': {error_type: count for error_type, count in errors_by_type},
            'top_error_groups': [
                {
                    'error_group': group,
                    'error_message': message,
                    'count': count,
                    'last_occurrence': last_occurrence.isoformat() if last_occurrence else None
                }
                for group, message, count, last_occurrence in top_groups
            ],
            'top_pages': [
                {'page_url': url, 'error_count': count}
                for url, count in top_pages
            ]
        }), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        if _is_missing_table_error(e):
            try:
                _ensure_error_logging_tables()
                return jsonify({
                    **_empty_error_stats(days)
                }), 200
            except Exception:
                return jsonify(_empty_error_stats(days)), 200
        return jsonify({
            'success': False,
            'error': 'Failed to get error stats',
            'message': str(e)
        }), 500
    except Exception as e:
        if _is_missing_table_error(e):
            return jsonify(_empty_error_stats(days)), 200
        return jsonify({
            'success': False,
            'error': 'Failed to get error stats',
            'message': str(e)
        }), 500


@error_logging_bp.route('/api/errors/resolve/<int:error_id>', methods=['POST'])
def resolve_error(error_id):
    """
    Mark an error as resolved
    
    Expected JSON:
    {
        "resolved_by": "admin_user_id",
        "resolution_notes": "Fixed by..."
    }
    """
    try:
        error = ErrorLog.query.get_or_404(error_id)
        data = request.get_json(silent=True) or {}
        
        error.is_resolved = True
        error.resolved_at = datetime.utcnow()
        error.resolved_by = data.get('resolved_by')
        error.resolution_notes = data.get('resolution_notes')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Error marked as resolved'
        }), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        if _is_missing_table_error(e):
            try:
                _ensure_error_logging_tables()
                return jsonify({
                    'success': False,
                    'message': 'Error table initialized; nothing to resolve',
                    'error_id': error_id
                }), 200
            except Exception:
                pass
        return jsonify({
            'success': False,
            'error': 'Failed to resolve error',
            'message': str(e)
        }), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to resolve error',
            'message': str(e)
        }), 500


@error_logging_bp.route('/api/errors/resolve-group/<error_group>', methods=['POST'])
def resolve_error_group(error_group):
    """
    Mark all errors in a group as resolved
    """
    try:
        data = request.get_json(silent=True) or {}
        
        errors = ErrorLog.query.filter(
            ErrorLog.error_group == error_group,
            ErrorLog.is_resolved == False
        ).all()
        
        resolved_by = data.get('resolved_by')
        resolution_notes = data.get('resolution_notes')
        
        for error in errors:
            error.is_resolved = True
            error.resolved_at = datetime.utcnow()
            error.resolved_by = resolved_by
            error.resolution_notes = resolution_notes
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Resolved {len(errors)} errors in group',
            'errors_resolved': len(errors)
        }), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        if _is_missing_table_error(e):
            try:
                _ensure_error_logging_tables()
                return jsonify({
                    'success': True,
                    'message': 'Error table initialized; no group rows to resolve',
                    'errors_resolved': 0
                }), 200
            except Exception:
                pass
        return jsonify({
            'success': False,
            'error': 'Failed to resolve error group',
            'message': str(e)
        }), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to resolve error group',
            'message': str(e)
        }), 500

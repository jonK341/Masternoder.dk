"""
Analytics & Monitoring Dashboard Routes
Comprehensive analytics for platform usage, performance, and health
"""
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from typing import Dict, Any, List
from src.db.models import db, Documentary, MovieClip
try:
    from src.db.models import GenerationStats
except ImportError:
    # GenerationStats might not exist, create a dummy class
    class GenerationStats:
        pass

# Import system_metrics with fallback
try:
    from src.utils.system_metrics import get_system_metrics
    SYSTEM_METRICS_AVAILABLE = True
except ImportError:
    SYSTEM_METRICS_AVAILABLE = False
    # Create dummy get_system_metrics function
    def get_system_metrics():
        class DummySystemMetrics:
            def get_request_stats(self): return {}
            def get_endpoint_stats(self): return {}
            def get_system_info(self): return {}
            def get_health_status(self): return {'status': 'unknown'}
        return DummySystemMetrics()

from src.utils.query_cache import cached_query

analytics_bp = Blueprint('analytics', __name__, url_prefix='')


@analytics_bp.route('/analytics')
@analytics_bp.route('/analytics/')
def analytics_index():
    """Analytics dashboard page"""
    from flask import send_from_directory, Response
    import os
    
    # Try serving from vidgenerator directory first (direct file serve)
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        vidgen_path = os.path.join(base_path, 'vidgenerator', 'analytics')
        index_file = os.path.join(vidgen_path, 'index.html')
        
        if os.path.exists(index_file):
            # Read file and return as response
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return Response(content, mimetype='text/html'), 200
    except Exception as file_error:
        print(f"[Analytics] File serve error: {file_error}")
    
    # Fallback HTML
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Analytics - masternoder.dk</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <h1>Analytics & Monitoring Dashboard</h1>
        <p>Analytics page - loading...</p>
        <p><a href="/vidgenerator">Back to main page</a></p>
    </body>
    </html>
    """, 200


@analytics_bp.route('/api/analytics/overview')
def get_analytics_overview():
    """Get overview analytics dashboard data"""
    try:
        @cached_query(ttl=300)  # Cache for 5 minutes
        def _get_overview_data():
            """Cached function to get overview analytics"""
            now = datetime.utcnow()
            today = now.date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Total videos
            total_videos = Documentary.query.filter_by(status='completed').count()
            videos_today = Documentary.query.filter(
                db.func.date(Documentary.created_at) == today,
                Documentary.status == 'completed'
            ).count()
            videos_this_week = Documentary.query.filter(
                Documentary.created_at >= week_ago,
                Documentary.status == 'completed'
            ).count()
            videos_this_month = Documentary.query.filter(
                Documentary.created_at >= month_ago,
                Documentary.status == 'completed'
            ).count()
            
            # Total duration
            total_duration = db.session.query(
                db.func.sum(Documentary.duration)
            ).filter_by(status='completed').scalar() or 0
            
            # Quality metrics
            avg_quality = db.session.query(
                db.func.avg(MovieClip.quality_score)
            ).scalar() or 0.0
            
            high_quality_count = MovieClip.query.filter(
                MovieClip.quality_score >= 0.8
            ).count()
            
            # Generation stats
            total_generations = Documentary.query.count()
            completed_generations = Documentary.query.filter_by(status='completed').count()
            failed_generations = Documentary.query.filter_by(status='failed').count()
            success_rate = (completed_generations / total_generations * 100) if total_generations > 0 else 0
            
            return {
                'videos': {
                    'total': total_videos,
                    'today': videos_today,
                    'this_week': videos_this_week,
                    'this_month': videos_this_month
                },
                'duration': {
                    'total_seconds': int(total_duration),
                    'total_hours': round(total_duration / 3600, 2),
                    'total_minutes': round(total_duration / 60, 2)
                },
                'quality': {
                    'average': float(avg_quality),
                    'high_quality_count': high_quality_count,
                    'high_quality_percentage': (high_quality_count / total_videos * 100) if total_videos > 0 else 0
                },
                'generations': {
                    'total': total_generations,
                    'completed': completed_generations,
                    'failed': failed_generations,
                    'success_rate': round(success_rate, 2)
                }
            }
        
        overview = _get_overview_data()
        
        return jsonify({
            'success': True,
            'overview': overview,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'overview': {}
        }), 500


@analytics_bp.route('/api/analytics/trends')
def get_analytics_trends():
    """Get usage trends over time"""
    try:
        days = int(request.args.get('days', 30))
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Get daily video counts
        daily_counts = db.session.query(
            db.func.date(Documentary.created_at).label('date'),
            db.func.count(Documentary.id).label('count')
        ).filter(
            Documentary.created_at >= start_date,
            Documentary.status == 'completed'
        ).group_by(
            db.func.date(Documentary.created_at)
        ).all()
        
        # Format for chart
        trends = {
            'dates': [],
            'counts': [],
            'cumulative': []
        }
        
        cumulative = 0
        current_date = start_date
        daily_dict = {str(d[0]): d[1] for d in daily_counts}
        
        while current_date <= end_date:
            date_str = str(current_date)
            count = daily_dict.get(date_str, 0)
            cumulative += count
            
            trends['dates'].append(date_str)
            trends['counts'].append(count)
            trends['cumulative'].append(cumulative)
            
            current_date += timedelta(days=1)
        
        return jsonify({
            'success': True,
            'trends': trends,
            'period': {
                'start': str(start_date),
                'end': str(end_date),
                'days': days
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'trends': {'dates': [], 'counts': [], 'cumulative': []}
        }), 500


@analytics_bp.route('/api/analytics/performance')
def get_performance_metrics():
    """Get performance metrics"""
    try:
        system_metrics = get_system_metrics()
        
        # Request statistics
        request_stats = system_metrics.get_request_stats()
        endpoint_stats = system_metrics.get_endpoint_stats()
        
        # System information
        system_info = system_metrics.get_system_info()
        
        # Health status
        health = system_metrics.get_health_status()
        
        # Generation performance (from GenerationStats if available)
        generation_performance = {}
        try:
            avg_gen_time = db.session.query(
                db.func.avg(GenerationStats.generation_time)
            ).scalar()
            
            if avg_gen_time:
                generation_performance = {
                    'average_generation_time': float(avg_gen_time),
                    'average_generation_time_formatted': f"{avg_gen_time:.2f}s"
                }
        except Exception:
            generation_performance = {}
        
        return jsonify({
            'success': True,
            'performance': {
                'requests': request_stats,
                'endpoints': endpoint_stats,
                'system': system_info,
                'health': health,
                'generation': generation_performance
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'performance': {}
        }), 500


@analytics_bp.route('/api/analytics/errors')
def get_error_analytics():
    """Get error tracking and analytics with Error.hash tracking"""
    try:
        # Import error hash tracking
        try:
            from backend.services.error_hash_tracking import error_hash_tracking
            error_hash_available = True
        except ImportError:
            error_hash_available = False
            error_hash_tracking = None
        
        # Get error hash analytics if available
        if error_hash_available and error_hash_tracking:
            hash_analytics = error_hash_tracking.get_error_analytics(limit=100)
            
            # Format for frontend
            errors_by_endpoint = []
            for endpoint_stat in hash_analytics.get('by_endpoint', []):
                errors_by_endpoint.append({
                    'endpoint': endpoint_stat['endpoint'],
                    'error_count': endpoint_stat['error_count'],
                    'request_count': 0,  # Will be updated from system metrics
                    'error_rate': 0,
                    'unique_errors': endpoint_stat['unique_errors'],
                    'error_hashes': endpoint_stat.get('errors', [])
                })
            
            return jsonify({
                'success': True,
                'errors': {
                    'total_errors': hash_analytics.get('total_errors', 0),
                    'total_requests': hash_analytics.get('total_requests', 0),
                    'overall_error_rate': hash_analytics.get('overall_error_rate', 0),
                    'unique_errors': hash_analytics.get('unique_errors', 0),
                    'by_endpoint': errors_by_endpoint[:20],  # Top 20
                    'by_hash': hash_analytics.get('by_hash', [])[:50],  # Top 50 by hash
                    'error_hash_tracking': True
                },
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Fallback to system metrics
        if SYSTEM_METRICS_AVAILABLE:
            system_metrics = get_system_metrics()
            endpoint_stats = system_metrics.get_endpoint_stats()
        else:
            endpoint_stats = {}
        
        # Extract error information
        errors = []
        total_errors = 0
        total_requests = 0
        
        for endpoint, stats in endpoint_stats.items():
            error_count = stats.get('error_count', 0)
            request_count = stats.get('request_count', 0)
            error_rate = stats.get('error_rate', 0)
            
            if error_count > 0:
                errors.append({
                    'endpoint': endpoint,
                    'error_count': error_count,
                    'request_count': request_count,
                    'error_rate': round(error_rate, 2)
                })
                total_errors += error_count
                total_requests += request_count
        
        # Sort by error count
        errors.sort(key=lambda x: x['error_count'], reverse=True)
        
        overall_error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        return jsonify({
            'success': True,
            'errors': {
                'total_errors': total_errors,
                'total_requests': total_requests,
                'overall_error_rate': round(overall_error_rate, 2),
                'by_endpoint': errors[:10],  # Top 10
                'error_hash_tracking': False
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'errors': {}
        }), 500


@analytics_bp.route('/api/analytics/quality')
def get_quality_analytics():
    """Get quality score analytics"""
    try:
        # Quality distribution
        quality_ranges = {
            'excellent': MovieClip.query.filter(MovieClip.quality_score >= 0.9).count(),
            'high': MovieClip.query.filter(
                MovieClip.quality_score >= 0.8,
                MovieClip.quality_score < 0.9
            ).count(),
            'medium': MovieClip.query.filter(
                MovieClip.quality_score >= 0.5,
                MovieClip.quality_score < 0.8
            ).count(),
            'low': MovieClip.query.filter(
                MovieClip.quality_score < 0.5,
                MovieClip.quality_score.isnot(None)
            ).count()
        }
        
        # Average quality over time
        avg_quality = db.session.query(
            db.func.avg(MovieClip.quality_score)
        ).scalar() or 0.0
        
        # Best quality
        best_quality = db.session.query(
            db.func.max(MovieClip.quality_score)
        ).scalar() or 0.0
        
        # Quality trends (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_clips = MovieClip.query.filter(
            MovieClip.created_at >= thirty_days_ago
        ).all()
        
        avg_recent = sum(c.quality_score or 0 for c in recent_clips) / len(recent_clips) if recent_clips else 0.0
        
        return jsonify({
            'success': True,
            'quality': {
                'distribution': quality_ranges,
                'average': float(avg_quality),
                'best': float(best_quality),
                'recent_average': float(avg_recent),
                'total_clips': sum(quality_ranges.values())
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'quality': {}
        }), 500


@analytics_bp.route('/api/analytics/usage')
def get_usage_analytics():
    """Get usage analytics by category, theme, etc."""
    try:
        # Videos by category
        category_usage = {}
        try:
            from src.services.content_categories import content_category_service
            categories = content_category_service.get_all_categories()
            for category in categories:
                cat_id = category.get('id')
                cat_name = category.get('name_da') or category.get('name')
                count = Documentary.query.filter_by(
                    category_name=cat_id,
                    status='completed'
                ).count()
                if count > 0:
                    category_usage[cat_name] = count
        except Exception:
            pass
        
        # Videos by quality level
        quality_levels = {
            'ULTRA': Documentary.query.filter_by(quality_level='ULTRA', status='completed').count(),
            'PREMIUM': Documentary.query.filter_by(quality_level='PREMIUM', status='completed').count(),
            'HIGH': Documentary.query.filter_by(quality_level='HIGH', status='completed').count(),
            'MEDIUM': Documentary.query.filter_by(quality_level='MEDIUM', status='completed').count(),
            'LOW': Documentary.query.filter_by(quality_level='LOW', status='completed').count()
        }
        
        # Status distribution
        status_distribution = {}
        for status in ['completed', 'generating', 'pending', 'failed']:
            count = Documentary.query.filter_by(status=status).count()
            if count > 0:
                status_distribution[status] = count
        
        return jsonify({
            'success': True,
            'usage': {
                'by_category': category_usage,
                'by_quality_level': quality_levels,
                'by_status': status_distribution
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'usage': {}
        }), 500


def register_analytics_routes(app):
    """Register analytics routes with Flask app"""
    app.register_blueprint(analytics_bp)
    print("[Routes] Analytics routes registered")


"""
Health Check Routes
Database health, system status, and monitoring endpoints
"""
import json
import os
import re
from flask import Blueprint, jsonify
from datetime import datetime
from sqlalchemy import text
from src.db.models import db

health_bp = Blueprint('health', __name__)

# App version for cache busting - bump on deploy to force client reload
APP_VERSION = "20260428a"


@health_bp.route('/api/version', methods=['GET'])
def version():
    """Return app version for cache busting and error detection. Clients fetch this to detect stale content."""
    return jsonify({
        'success': True,
        'version': APP_VERSION,
        'timestamp': datetime.utcnow().isoformat(),
    }), 200, {
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        'X-Content-Version': APP_VERSION,
    }


@health_bp.route('/api/health', methods=['GET'])
def health_check():
    """Basic health check"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@health_bp.route('/api/health/database', methods=['GET'])
def database_health():
    """Database health check"""
    try:
        # Test database connection
        result = db.session.execute(text("SELECT 1"))
        result.fetchone()
        
        # Tables that db.create_all() creates from src.db.models (single source of truth).
        # Do not list legacy names that have no SQLAlchemy model — they would always be "missing".
        tables_to_check = [
            'user_accounts', 'user_profiles',
            'player_levels', 'user_points', 'xp_history', 'system_point_snapshots',
            'shop_items', 'user_inventory', 'shop_purchases',
            'battle_matches', 'user_storage',
        ]
        existing_tables = []
        missing_tables = []
        
        for table in tables_to_check:
            try:
                db.session.execute(text(f"SELECT COUNT(*) FROM {table} LIMIT 1"))
                existing_tables.append(table)
            except Exception:
                missing_tables.append(table)
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'database': {
                'connected': True,
                'tables_checked': len(tables_to_check),
                'existing_tables': existing_tables,
                'missing_tables': missing_tables
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'database': {
                'connected': False
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 503


def _mask_db_url(url: str) -> str:
    if not url:
        return ''
    return re.sub(r'(:)([^/@]+)(@)', r':***\3', url, count=1)


@health_bp.route('/api/health/data-schema', methods=['GET'])
def data_schema_health():
    """
    Schema / migration diagnostics: required tables, optional ledger rows,
    unified_points file store size. Use when debugger migration % or points look stuck.
    """
    out = {
        'success': True,
        'timestamp': datetime.utcnow().isoformat(),
        'database_engine': None,
        'tables': {},
        'schema_migrations_recent': [],
        'unified_points_files': {'count': 0, 'directory': None},
    }
    try:
        uri = str(db.engine.url)
        out['database_engine'] = _mask_db_url(uri)
    except Exception:
        pass

    required = (
        'player_levels', 'system_point_snapshots', 'point_transactions',
        'shop_purchases', 'user_inventory', 'shop_items', 'schema_migrations',
    )
    for t in required:
        try:
            db.session.execute(text(f'SELECT COUNT(*) FROM {t}'))
            cnt = db.session.execute(text(f'SELECT COUNT(*) FROM {t}')).scalar()
            out['tables'][t] = {'present': True, 'row_count': int(cnt or 0)}
        except Exception as e:
            out['tables'][t] = {'present': False, 'error': str(e)[:200]}

    try:
        rows = db.session.execute(
            text(
                'SELECT script_name, status, applied_at FROM schema_migrations ORDER BY applied_at DESC LIMIT 8'
            )
        ).fetchall()
        out['schema_migrations_recent'] = [
            {'script_name': r[0], 'status': r[1], 'applied_at': str(r[2]) if r[2] else None}
            for r in (rows or [])
        ]
    except Exception:
        out['schema_migrations_recent'] = []

    try:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        upd = os.path.join(base, 'logs', 'unified_points')
        out['unified_points_files']['directory'] = upd
        if os.path.isdir(upd):
            out['unified_points_files']['count'] = len([f for f in os.listdir(upd) if f.endswith('.json')])
    except Exception:
        pass

    present = sum(1 for v in out['tables'].values() if v.get('present'))
    out['summary'] = {
        'required_tables_present': f'{present}/{len(required)}',
        'all_core_present': present >= len(required) - 1,
    }
    return jsonify(out), 200


@health_bp.route('/api/health/system', methods=['GET'])
def system_health():
    """System health check - checks all components"""
    health_status = {
        'overall': 'healthy',
        'components': {},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Check database
    try:
        db.session.execute(text("SELECT 1"))
        health_status['components']['database'] = {'status': 'healthy', 'connected': True}
    except Exception as e:
        health_status['components']['database'] = {'status': 'unhealthy', 'error': str(e)}
        health_status['overall'] = 'degraded'
    
    # Check unified points system
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            health_status['components']['unified_points'] = {'status': 'healthy', 'available': True}
        else:
            health_status['components']['unified_points'] = {'status': 'unavailable', 'available': False}
            health_status['overall'] = 'degraded'
    except Exception as e:
        health_status['components']['unified_points'] = {'status': 'unhealthy', 'error': str(e)}
        health_status['overall'] = 'degraded'
    
    # Check error logging
    try:
        from backend.middleware.error_logging_middleware import error_logger
        health_status['components']['error_logging'] = {'status': 'healthy', 'available': True}
    except Exception as e:
        health_status['components']['error_logging'] = {'status': 'unhealthy', 'error': str(e)}
    
    # Check caching
    try:
        from backend.middleware.response_cache_middleware import get_cache_stats
        cache_stats = get_cache_stats()
        health_status['components']['caching'] = {
            'status': 'healthy',
            'cache_entries': cache_stats.get('total_entries', 0)
        }
    except Exception as e:
        health_status['components']['caching'] = {'status': 'unhealthy', 'error': str(e)}
    
    # Check rate limiting
    try:
        from backend.middleware.rate_limit_middleware import _LIMITS
        health_status['components']['rate_limiting'] = {
            'status': 'healthy',
            'configured_endpoints': len([k for k in _LIMITS.keys() if k != 'default'])
        }
    except Exception as e:
        health_status['components']['rate_limiting'] = {'status': 'unhealthy', 'error': str(e)}

    # MN2 RPC (Phase 1): optional; if unreachable, try Chainz fallback for block height (Phase 7)
    try:
        from backend.services.mn2_rpc_client import health_check as mn2_health_check
        mn2 = mn2_health_check()
        block_height = mn2.get('block_height')
        status = mn2.get('status', 'unknown')
        # Only use Chainz when RPC is unreachable — not when auth_failed (would hide 401 misconfig)
        if status == 'unreachable':
            try:
                from backend.services.mn2_chainz import chainz_getblockcount
                chainz_height = chainz_getblockcount()
                if chainz_height is not None:
                    block_height = chainz_height
                    status = 'degraded_fallback'  # RPC down but Chainz gave block height
            except Exception:
                pass
        health_status['components']['mn2_rpc'] = {
            'status': status,
            'block_height': block_height,
            'latency_ms': mn2.get('latency_ms'),
        }
        if mn2.get('credentials'):
            health_status['components']['mn2_rpc']['credentials'] = mn2['credentials']
        if mn2.get('error'):
            health_status['components']['mn2_rpc']['error'] = mn2['error']
        if status in ('unreachable', 'degraded_fallback', 'auth_failed'):
            health_status['overall'] = 'degraded'
    except Exception as e:
        health_status['components']['mn2_rpc'] = {'status': 'unreachable', 'error': str(e)}
        health_status['overall'] = 'degraded'

    try:
        from backend.services.worker_pressure_service import worker_pressure
        wp = worker_pressure()
        health_status['components']['worker_pressure'] = wp
        if wp.get('recommendation') == 'throttle':
            health_status['overall'] = 'degraded'
    except Exception as e:
        health_status['components']['worker_pressure'] = {'status': 'unavailable', 'error': str(e)}

    status_code = 200 if health_status['overall'] == 'healthy' else 503
    
    return jsonify({
        'success': True,
        **health_status
    }), status_code


@health_bp.route('/api/mn2/health', methods=['GET'])
def mn2_health():
    """Dedicated MN2 health: RPC, block monotonicity, deposit scanner, staking."""
    from datetime import datetime, timezone
    out = {
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'components': {},
    }
    degraded = False

    try:
        from backend.services.mn2_rpc_client import health_check as mn2_health_check
        mn2 = mn2_health_check()
        block_height = mn2.get('block_height')
        rpc_status = mn2.get('status', 'unknown')
        if rpc_status == 'unreachable':
            try:
                from backend.services.mn2_chainz import chainz_getblockcount
                chainz_height = chainz_getblockcount()
                if chainz_height is not None:
                    block_height = chainz_height
                    rpc_status = 'degraded_fallback'
            except Exception:
                pass
        out['components']['mn2_rpc'] = {
            'status': rpc_status,
            'block_height': block_height,
            'latency_ms': mn2.get('latency_ms'),
        }
        if mn2.get('error'):
            out['components']['mn2_rpc']['error'] = mn2['error']
        if rpc_status in ('unreachable', 'degraded_fallback', 'auth_failed'):
            degraded = True
    except Exception as exc:
        out['components']['mn2_rpc'] = {'status': 'unreachable', 'error': str(exc)}
        degraded = True

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    hist_path = os.path.join(base, 'data', 'mn2_network_history.jsonl')
    try:
        last_height = None
        prev_height = None
        if os.path.isfile(hist_path):
            with open(hist_path, 'r', encoding='utf-8') as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()][-2:]
            for ln in lines:
                row = json.loads(ln)
                h = row.get('block_height') or row.get('height')
                if h is not None:
                    prev_height = last_height
                    last_height = int(h)
        mono_ok = last_height is None or prev_height is None or last_height >= prev_height
        out['components']['block_monotonicity'] = {
            'status': 'healthy' if mono_ok else 'degraded',
            'last_height': last_height,
            'prev_height': prev_height,
        }
        if not mono_ok:
            degraded = True
    except Exception as exc:
        out['components']['block_monotonicity'] = {'status': 'unknown', 'error': str(exc)}

    try:
        scan_log = os.path.join(base, 'logs', 'mn2_deposit_scanner.jsonl')
        last_run = None
        if os.path.isfile(scan_log):
            with open(scan_log, 'r', encoding='utf-8') as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
            if lines:
                last_run = json.loads(lines[-1])
        out['components']['deposit_scanner'] = {
            'status': 'healthy' if last_run else 'unknown',
            'last_run': last_run,
        }
    except Exception as exc:
        out['components']['deposit_scanner'] = {'status': 'unknown', 'error': str(exc)}

    try:
        from backend.services.mn2_staking_service import get_config
        cfg = get_config()
        out['components']['staking'] = {
            'status': 'healthy' if cfg.get('enabled') else 'disabled',
            'enabled': bool(cfg.get('enabled')),
        }
    except Exception as exc:
        out['components']['staking'] = {'status': 'unknown', 'error': str(exc)}

    if degraded:
        out['status'] = 'degraded'
    code = 200 if out['status'] == 'healthy' else 503
    return jsonify(out), code

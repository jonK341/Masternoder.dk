"""
Health Check Routes
Database health, system status, and monitoring endpoints
"""
import json
import os
import re
from flask import Blueprint, jsonify
from datetime import datetime
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from src.db.models import db

_DB_REQUIRED_TABLES = (
    'user_accounts', 'user_profiles',
    'player_levels', 'user_points', 'xp_history', 'system_point_snapshots',
    'shop_items', 'user_inventory', 'shop_purchases',
)
_DB_OPTIONAL_TABLES = ('battle_matches', 'user_storage')

from backend.services.schema_bootstrap import SCHEMA_MIGRATIONS_HEALTH_COLUMNS

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
    """Database health check — fast metadata probe; 503 only when DB is unreachable."""
    try:
        result = db.session.execute(text("SELECT 1"))
        result.fetchone()

        table_names = set()
        try:
            table_names = set(sa_inspect(db.engine).get_table_names())
        except Exception:
            pass

        existing_required = [t for t in _DB_REQUIRED_TABLES if t in table_names]
        missing_required = [t for t in _DB_REQUIRED_TABLES if t not in table_names]
        existing_optional = [t for t in _DB_OPTIONAL_TABLES if t in table_names]
        missing_optional = [t for t in _DB_OPTIONAL_TABLES if t not in table_names]
        db_status = 'healthy' if not missing_required else 'degraded'

        return jsonify({
            'success': True,
            'status': db_status,
            'database': {
                'connected': True,
                'required_tables': existing_required,
                'missing_required_tables': missing_required,
                'optional_tables': existing_optional,
                'missing_optional_tables': missing_optional,
                'apply_battle_migration': (
                    'python scripts/battle_migration.py --standalone'
                    if 'battle_matches' in missing_optional
                    else None
                ),
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
        columns = ", ".join(SCHEMA_MIGRATIONS_HEALTH_COLUMNS)
        rows = db.session.execute(
            text(
                f"SELECT {columns} FROM schema_migrations ORDER BY applied_at DESC LIMIT 8"
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

    # Battle durable history (optional until scripts/battle_migration.py is applied)
    try:
        from backend.services.battle_db_service import battle_tables_exist
        battle_ok = battle_tables_exist()
        health_status['components']['battle_matches'] = {
            'status': 'healthy' if battle_ok else 'optional_missing',
            'table_present': battle_ok,
            'apply_migration': 'python scripts/battle_migration.py --standalone' if not battle_ok else None,
        }
    except Exception as e:
        health_status['components']['battle_matches'] = {'status': 'unknown', 'error': str(e)}
    
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

    # MN2 RPC: short timeout on this path (no Chainz fallback — keeps /api/health/system fast).
    try:
        from backend.services.mn2_rpc_client import health_check as mn2_health_check
        try:
            sys_rpc_to = float((os.environ.get("MN2_RPC_SYSTEM_HEALTH_TIMEOUT") or "3").strip() or 3)
        except (TypeError, ValueError):
            sys_rpc_to = 3.0
        mn2 = mn2_health_check(timeout_sec=sys_rpc_to)
        status = mn2.get('status', 'unknown')
        health_status['components']['mn2_rpc'] = {
            'status': status,
            'block_height': mn2.get('block_height'),
            'latency_ms': mn2.get('latency_ms'),
            'timeout_sec': sys_rpc_to,
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

    try:
        from backend.services.profit_daemon_background_ops_service import profit_daemon_health_probe
        pd = profit_daemon_health_probe(alert_on_stale=True)
        health_status['components']['profit_daemon'] = pd
        if pd.get('status') == 'offline':
            health_status['overall'] = 'degraded'
    except Exception as e:
        health_status['components']['profit_daemon'] = {'status': 'unavailable', 'error': str(e)}

    # Always HTTP 200 so nginx/load checks get a body; use overall=degraded for signal.
    return jsonify({
        'success': True,
        **health_status
    }), 200


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

    try:
        from backend.services.mn2_rpc_client import staking_health
        sh = staking_health() or {}
        minting = sh.get('status') == 'active' or sh.get('staking_active') is True
        out['components']['daemon_staking'] = {
            'status': sh.get('status') or ('active' if minting else 'inactive'),
            'staking_active': bool(sh.get('staking_active')),
            'mnsync': sh.get('mnsync'),
            'have_connections': sh.get('have_connections'),
            'walletunlocked': sh.get('walletunlocked'),
        }
        if sh.get('status') == 'inactive' or sh.get('staking_active') is False:
            degraded = True
    except Exception as exc:
        out['components']['daemon_staking'] = {'status': 'unknown', 'error': str(exc)}

    try:
        from backend.services.discord_service import outbox_stats
        out['components']['discord_outbox'] = outbox_stats(30)
        if out['components']['discord_outbox'].get('status') == 'degraded':
            degraded = True
    except Exception as exc:
        out['components']['discord_outbox'] = {'status': 'unknown', 'error': str(exc)}

    try:
        from backend.services import mn2_network_stats
        alerts = mn2_network_stats.get_alerts(limit=5)
        out['components']['network_alerts'] = {
            'status': 'healthy' if not alerts else 'warn',
            'recent_count': len(alerts),
            'latest': alerts[0] if alerts else None,
        }
    except Exception as exc:
        out['components']['network_alerts'] = {'status': 'unknown', 'error': str(exc)}

    try:
        from backend.services import mn2_masternode_service
        out['components']['masternode_hosting'] = mn2_masternode_service.probe_health()
        mh = out['components']['masternode_hosting']
        if mh.get('status') in ('degraded', 'warn') and mh.get('enabled'):
            degraded = True
    except Exception as exc:
        out['components']['masternode_hosting'] = {'status': 'unknown', 'error': str(exc)}

    # Avoid building the full services catalog on the health path — it re-probes
    # PoR/RPC and was a major contributor to worker starvation. Peek cache only.
    try:
        from backend.services import mn2_services_hub
        peek = getattr(mn2_services_hub, "peek_catalog_cache", None)
        catalog = peek() if callable(peek) else None
        if catalog:
            out['components']['mn2_services'] = {
                'status': (catalog.get('summary') or {}).get('overall') or 'unknown',
                'summary': catalog.get('summary'),
                'service_count': len(catalog.get('services') or []),
                'cached': True,
            }
        else:
            out['components']['mn2_services'] = {
                'status': 'unknown',
                'detail': 'catalog cache cold',
            }
    except Exception as exc:
        out['components']['mn2_services'] = {'status': 'unknown', 'error': str(exc)}

    if degraded:
        out['status'] = 'degraded'
    code = 200 if out['status'] == 'healthy' else 503
    return jsonify(out), code

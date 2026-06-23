"""
Trophies Routes
Routes for trophy display and management
Supports both /trophies (plural) and /trophie (singular) for compatibility
All endpoints resolve user_id via session > query > identification.
"""
from flask import Blueprint, jsonify, request
import os
import json
import threading


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        return request.args.get('user_id', 'default_user')


_DEFINITIONS_CACHE = {'mtime': None, 'data': None}
_DEFINITIONS_LOCK = threading.Lock()


def _definitions_path() -> str:
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, 'data', 'trophy_definitions.json')


def load_trophy_definitions_file():
    """Load trophy definitions from data/trophy_definitions.json (cached, reloads on file change).

    Returns a dict: {'version', 'updated', 'trophies': [ {...}, ... ]}.
    This JSON file is the single source of truth for trophy definitions.
    """
    path = _definitions_path()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {'version': '0', 'trophies': []}
    with _DEFINITIONS_LOCK:
        if _DEFINITIONS_CACHE['mtime'] == mtime and _DEFINITIONS_CACHE['data'] is not None:
            return _DEFINITIONS_CACHE['data']
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict) or not isinstance(data.get('trophies'), list):
                data = {'version': '0', 'trophies': []}
        except (OSError, ValueError):
            data = {'version': '0', 'trophies': []}
        _DEFINITIONS_CACHE['mtime'] = mtime
        _DEFINITIONS_CACHE['data'] = data
        return data


def _definitions_by_id() -> dict:
    data = load_trophy_definitions_file()
    out = {}
    for t in data.get('trophies', []):
        tid = t.get('id')
        if tid:
            out[str(tid)] = t
    return out


def save_trophy_definitions_file(data: dict) -> bool:
    """Write the definitions file and invalidate the cache (admin authoring, Feature 25)."""
    path = _definitions_path()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with _DEFINITIONS_LOCK:
            _DEFINITIONS_CACHE['mtime'] = None
            _DEFINITIONS_CACHE['data'] = None
        return True
    except OSError:
        return False


def validate_definitions() -> dict:
    """Validate the definitions file; returns {'ok': bool, 'errors': [...], 'warnings': [...]}."""
    from datetime import datetime
    data = load_trophy_definitions_file()
    trophies = data.get('trophies', [])
    sets = data.get('sets', [])
    errors, warnings = [], []
    seen = set()
    ids = set()
    for t in trophies:
        tid = t.get('id')
        if not tid:
            errors.append('Trophy missing id: ' + str(t.get('name')))
            continue
        if tid in seen:
            errors.append('Duplicate trophy id: ' + str(tid))
        seen.add(tid)
        ids.add(str(tid))
        if t.get('reward') is None:
            warnings.append('Trophy missing reward: ' + str(tid))
        if not t.get('rarity'):
            warnings.append('Trophy missing rarity: ' + str(tid))
        if bool(t.get('progress_metric')) != bool(t.get('progress_target')):
            warnings.append('Trophy has metric/target mismatch: ' + str(tid))
        for k in ('available_from', 'available_until'):
            if t.get(k):
                try:
                    datetime.strptime(t[k], '%Y-%m-%d')
                except (ValueError, TypeError):
                    errors.append('Invalid ' + k + ' on ' + str(tid) + ': ' + str(t.get(k)))
    for s in sets:
        for m in (s.get('members') or []):
            if str(m) not in ids:
                errors.append('Set ' + str(s.get('id')) + ' references unknown trophy: ' + str(m))
    return {'ok': not errors, 'errors': errors, 'warnings': warnings,
            'trophy_count': len(trophies), 'set_count': len(sets)}


def _admin_authorized() -> bool:
    """Trophy authoring is disabled unless TROPHY_ADMIN_SECRET is set and matched (safe by default)."""
    secret = (os.environ.get('TROPHY_ADMIN_SECRET') or '').strip()
    if not secret:
        return False
    token = (request.headers.get('X-Trophy-Admin-Token') or request.args.get('admin_token') or '').strip()
    return token == secret


def compute_user_metrics(user_id: str) -> dict:
    """Server-side progress metrics from the unified points DB (mirrors the frontend).

    Best-effort: only metrics we can reliably derive are populated.
    """
    metrics = {'generation_points': 0, 'total_points': 0, 'videos': 0,
               'level': 0, 'trophies': 0, 'achievements': 0}
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db and hasattr(unified_points_db, 'get_all_points'):
            res = unified_points_db.get_all_points(user_id) or {}
            points = res.get('points', res) if isinstance(res, dict) else {}
            num = lambda k: float(points.get(k, 0) or 0)
            gen = num('generation_points')
            buckets = ['generation_points', 'activity_points', 'battle_points', 'quest_points',
                       'game_points', 'social_points', 'knowledge_points', 'crypto_points']
            metrics['generation_points'] = gen
            metrics['total_points'] = sum(num(b) for b in buckets)
            metrics['videos'] = int(gen / 25)
            metrics['level'] = num('level')
            metrics['achievements'] = num('achievements_earned')
            metrics['trophies'] = num('trophies_collected')
    except Exception:
        pass
    # Trophy count from DB unlocks (authoritative when available)
    try:
        from backend.services.trophies_db_service import get_user_trophies
        unlocked = get_user_trophies(user_id) or []
        if unlocked:
            metrics['trophies'] = max(metrics.get('trophies', 0), len(unlocked))
    except Exception:
        pass
    return metrics


def _seasonal_available(defn: dict, today: 'date' = None) -> bool:
    """True if a seasonal trophy is currently within its availability window.

    Non-seasonal trophies (no available_from/until) are always available.
    """
    from datetime import date as _date
    fmt = '%Y-%m-%d'
    start = defn.get('available_from')
    end = defn.get('available_until')
    if not start and not end:
        return True
    today = today or _date.today()
    try:
        from datetime import datetime
        if start and today < datetime.strptime(start, fmt).date():
            return False
        if end and today > datetime.strptime(end, fmt).date():
            return False
    except Exception:
        return True
    return True


def eligible_trophy_ids(metrics: dict, already_unlocked=None) -> list:
    """Trophy ids whose progress_metric has reached its target and are currently available."""
    already = set(str(x) for x in (already_unlocked or []))
    out = []
    for tid, d in _definitions_by_id().items():
        if tid in already:
            continue
        metric = d.get('progress_metric')
        target = d.get('progress_target')
        if not metric or not target:
            continue
        if float(metrics.get(metric, 0) or 0) < float(target):
            continue
        if not _seasonal_available(d):
            continue
        out.append(tid)
    return out


trophies_bp = Blueprint('trophies', __name__)

@trophies_bp.route('/vidgenerator/trophies')
@trophies_bp.route('/vidgenerator/trophies/')
@trophies_bp.route('/trophies')
@trophies_bp.route('/trophies/')
# Also support singular for backwards compatibility
@trophies_bp.route('/vidgenerator/trophie')
@trophies_bp.route('/vidgenerator/trophie/')
@trophies_bp.route('/trophie')
@trophies_bp.route('/trophie/')
def trophies_index():
    """Trophies page - serves the HTML file"""
    try:
        # Get the base path (project root)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Prefer root trophies/index.html (canonical after the move from vidgenerator/),
        # fall back to the legacy vidgenerator/trophies/ path.
        trophies_path = os.path.join(base_path, 'trophies', 'index.html')
        if not os.path.exists(trophies_path):
            trophies_path = os.path.join(base_path, 'vidgenerator', 'trophies', 'index.html')

        if os.path.exists(trophies_path):
            with open(trophies_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
        # Fallback HTML if file doesn't exist
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trophies - MasterNoder</title>
    <link rel="stylesheet" href="/vidgenerator/static/css/modern-design-system.css">
    <link rel="stylesheet" href="/vidgenerator/static/css/navigation-toolbar.css">
    <style>
        body { 
            padding: 100px 20px 60px; 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%);
            color: #ffffff;
        }
        .trophies-container {
            max-width: 1600px;
            margin: 0 auto;
        }
        .trophies-header {
            text-align: center;
            padding: 40px 20px;
            margin-bottom: 40px;
        }
        .trophies-header h1 {
            font-size: 4rem;
            font-weight: 900;
            margin: 0;
            background: linear-gradient(135deg, #FFD700, #FFA500);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .trophy-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); 
            gap: 20px; 
            margin-top: 20px; 
        }
        .trophy-card { 
            padding: 20px; 
            border: 2px solid rgba(255, 215, 0, 0.3); 
            border-radius: 8px; 
            text-align: center;
            background: rgba(21, 21, 32, 0.8);
        }
        .trophy-card h3 {
            color: #FFD700;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div id="navigation-toolbar"></div>
    <div class="trophies-container">
        <div class="trophies-header">
            <h1>🏆 Trophies</h1>
            <p>Your achievements and accomplishments</p>
        </div>
        <div id="trophies-container">
            <p>Loading trophies...</p>
        </div>
    </div>
    <script src="/vidgenerator/static/js/navigation-toolbar.js"></script>
    <script>
        // Load trophies
        fetch('/api/trophies/list')
            .then(r => r.json())
            .catch(() => fetch('/api/trophie/list'))
            .then(r => r.json())
            .then(data => {
                const container = document.getElementById('trophies-container');
                if (data.success && data.trophies) {
                    container.innerHTML = '<div class="trophy-grid">' + 
                        data.trophies.map(t => `<div class="trophy-card"><h3>${t.name || t}</h3></div>`).join('') +
                        '</div>';
                } else {
                    container.innerHTML = '<p>No trophies found. Start earning trophies by playing!</p>';
                }
            })
            .catch(e => {
                console.error('Error loading trophies:', e);
                document.getElementById('trophies-container').innerHTML = 
                    '<p>Error loading trophies. Please try again later.</p>';
            });
    </script>
</body>
</html>"""
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        return f"Error loading trophies page: {str(e)}", 500

@trophies_bp.route('/api/trophies/definitions')
@trophies_bp.route('/api/trophie/definitions')
def trophy_definitions_api():
    """Single source of truth for trophy definitions (from data/trophy_definitions.json)."""
    try:
        data = load_trophy_definitions_file()
        trophies = data.get('trophies', [])
        return jsonify({
            'success': True,
            'version': data.get('version', '0'),
            'updated': data.get('updated'),
            'count': len(trophies),
            'trophies': trophies,
            'sets': data.get('sets', []),
            'definitions': {str(t['id']): t for t in trophies if t.get('id')},
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trophies_bp.route('/api/trophies/list')
# Also support singular for backwards compatibility
@trophies_bp.route('/api/trophie/list')
def list_trophies_api():
    """List all trophies API.

    Definitions come from the JSON source of truth (data/trophy_definitions.json);
    DB/legacy definitions are merged in as a supplement. User unlocks come from the
    DB (when migration is run) and legacy trophy_system.
    """
    try:
        user_id = _resolve_uid()
        trophies = []
        # 1) Canonical definitions from the JSON source of truth
        definitions = dict(_definitions_by_id())
        # 2) DB definitions + user unlocks (supplement / override when present)
        try:
            from backend.services.trophies_db_service import get_trophy_definitions, get_user_trophies
            definitions_list = get_trophy_definitions()
            trophies = get_user_trophies(user_id)
            for d in (definitions_list or []):
                if d.get('id'):
                    merged = dict(definitions.get(str(d['id']), {}))
                    merged.update({k: v for k, v in d.items() if v not in (None, '')})
                    definitions[str(d['id'])] = merged
        except Exception:
            pass
        # 3) Legacy trophy_system (only if we still have no unlocks)
        if not trophies:
            try:
                from backend.services.trophy_system import trophy_system
                trophies = trophy_system.get_user_trophies(user_id) or []
                legacy_defs = getattr(trophy_system, 'trophy_definitions', {}) or {}
                for tid, d in legacy_defs.items():
                    if str(tid) not in definitions and isinstance(d, dict):
                        definitions[str(tid)] = {'id': tid, **d}
            except ImportError:
                pass
        return jsonify({
            'success': True,
            'trophies': trophies,
            'definitions': definitions,
            'count': len(definitions),
            'user_id': user_id,
            'source': 'json+db' if definitions else 'empty',
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@trophies_bp.route('/api/trophies/award', methods=['POST'])
# Also support singular for backwards compatibility
@trophies_bp.route('/api/trophie/award', methods=['POST'])
def award_trophy_api():
    """Award a trophy to a user (recorded in DB when migration run)."""
    try:
        data = request.get_json() or {}
        user_id = _resolve_uid()
        trophy_id = data.get('trophy_id')
        if not trophy_id:
            return jsonify({'success': False, 'error': 'trophy_id is required'}), 400
        recorded = False
        defn = _definitions_by_id().get(str(trophy_id), {})
        reward = defn.get('reward')
        try:
            from backend.services.trophies_db_service import award_trophy
            recorded = award_trophy(user_id, trophy_id, reward=reward)
        except Exception:
            pass
        result = {'message': 'Trophy awarded' if recorded else 'Trophy awarded (simulated)'}
        try:
            from backend.services.trophy_system import trophy_system
            result = trophy_system.award_trophy(user_id, trophy_id)
        except ImportError:
            pass
        return jsonify({
            'success': True,
            'user_id': user_id,
            'trophy_id': trophy_id,
            'reward': reward,
            **result
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trophies_bp.route('/api/trophies/sync', methods=['POST'])
@trophies_bp.route('/api/trophie/sync', methods=['POST'])
def sync_trophies_api():
    """Server-side unlock wiring (Feature 16).

    Computes the user's real progress metrics from the unified points DB, awards any
    trophies that have met their target (and are currently available), and returns the
    newly unlocked trophies plus the current metrics. Idempotent: re-running awards nothing
    new. Replaces client-side guessing about what should be unlocked.
    """
    try:
        user_id = _resolve_uid()
        metrics = compute_user_metrics(user_id)
        # Currently unlocked ids (DB)
        already = set()
        try:
            from backend.services.trophies_db_service import get_user_trophies
            already = {str(t.get('id')) for t in (get_user_trophies(user_id) or [])}
        except Exception:
            pass
        defs = _definitions_by_id()
        newly = []
        for tid in eligible_trophy_ids(metrics, already):
            reward = defs.get(tid, {}).get('reward')
            recorded = False
            try:
                from backend.services.trophies_db_service import award_trophy
                recorded = award_trophy(user_id, tid, reward=reward)
            except Exception:
                pass
            if recorded:
                newly.append({'id': tid, 'name': defs.get(tid, {}).get('name', tid), 'reward': reward,
                              'rarity': defs.get(tid, {}).get('rarity', 'common'),
                              'icon': defs.get(tid, {}).get('icon', '🏆')})
        return jsonify({
            'success': True,
            'user_id': user_id,
            'metrics': metrics,
            'newly_unlocked': newly,
            'newly_unlocked_count': len(newly),
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trophies_bp.route('/api/trophies/claim', methods=['POST'])
@trophies_bp.route('/api/trophie/claim', methods=['POST'])
def claim_trophy_api():
    """Reward claim flow (Feature 13).

    Records the unlock (idempotent) and credits the trophy's reward to trophy_points.
    Safe to call repeatedly: INSERT OR IGNORE means the reward is credited at most once.
    """
    try:
        data = request.get_json() or {}
        user_id = _resolve_uid()
        trophy_id = data.get('trophy_id')
        if not trophy_id:
            return jsonify({'success': False, 'error': 'trophy_id is required'}), 400
        defn = _definitions_by_id().get(str(trophy_id), {})
        reward = defn.get('reward')
        # Only allow claiming trophies the user has actually met (or already unlocked)
        already_owned = False
        try:
            from backend.services.trophies_db_service import get_user_trophies
            already_owned = str(trophy_id) in {str(t.get('id')) for t in (get_user_trophies(user_id) or [])}
        except Exception:
            pass
        if not already_owned:
            metrics = compute_user_metrics(user_id)
            metric, target = defn.get('progress_metric'), defn.get('progress_target')
            meets = bool(metric and target and float(metrics.get(metric, 0) or 0) >= float(target))
            if not (meets and _seasonal_available(defn)):
                return jsonify({'success': False, 'error': 'Trophy requirement not met', 'trophy_id': trophy_id}), 400
        recorded = False
        try:
            from backend.services.trophies_db_service import award_trophy
            recorded = award_trophy(user_id, trophy_id, reward=reward)
        except Exception:
            pass
        return jsonify({
            'success': True,
            'user_id': user_id,
            'trophy_id': trophy_id,
            'reward': reward,
            'recorded': recorded,
            'already_owned': already_owned,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trophies_bp.route('/api/trophies/quests')
@trophies_bp.route('/api/trophie/quests')
def trophy_quests_api():
    """Daily and weekly trophy quests (Feature 10).

    Deterministically picks objectives from trophy categories seeded by the date so all
    users see the same rotation, and marks completion against the user's unlocked trophies.
    """
    try:
        import hashlib
        from datetime import date, timedelta
        user_id = _resolve_uid()
        defs = _definitions_by_id()
        # Group non-seasonal, non-hidden trophies by category
        by_cat = {}
        for tid, d in defs.items():
            if d.get('hidden') or d.get('category') == 'seasonal':
                continue
            by_cat.setdefault(d.get('category', 'special'), []).append(tid)
        cats = sorted(by_cat.keys())

        already = set()
        try:
            from backend.services.trophies_db_service import get_user_trophies
            already = {str(t.get('id')) for t in (get_user_trophies(user_id) or [])}
        except Exception:
            pass

        def seeded_index(seed_str, modulo):
            h = int(hashlib.sha256(seed_str.encode('utf-8')).hexdigest(), 16)
            return h % max(1, modulo)

        def make_quest(seed_str, scope, expires_iso):
            if not cats:
                return None
            cat = cats[seeded_index(seed_str + ':cat', len(cats))]
            members = sorted(by_cat[cat])
            completed = sum(1 for m in members if m in already)
            return {
                'id': scope + '_' + seed_str,
                'scope': scope,
                'category': cat,
                'title': ('Daily' if scope == 'daily' else 'Weekly') + ': unlock a ' + cat + ' trophy',
                'target': 1 if scope == 'daily' else 3,
                'progress': completed,
                'complete': completed >= (1 if scope == 'daily' else 3),
                'reward': 100 if scope == 'daily' else 500,
                'expires': expires_iso,
            }

        today = date.today()
        # Weekly window starts Monday
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=7)
        quests = []
        dq = make_quest(today.isoformat(), 'daily', (today + timedelta(days=1)).isoformat())
        wq = make_quest(week_start.isoformat(), 'weekly', week_end.isoformat())
        if dq:
            quests.append(dq)
        if wq:
            quests.append(wq)
        return jsonify({'success': True, 'user_id': user_id, 'quests': quests, 'date': today.isoformat()}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trophies_bp.route('/api/trophies/leaderboard')
@trophies_bp.route('/api/trophie/leaderboard')
def trophy_leaderboard_api():
    """Top trophy collectors ranked by trophy points (Feature 17)."""
    try:
        user_id = _resolve_uid()
        try:
            limit = min(100, max(1, int(request.args.get('limit', 25))))
        except (TypeError, ValueError):
            limit = 25
        from backend.services.trophy_social_service import get_leaderboard
        result = get_leaderboard(limit=limit, current_user=user_id)
        return jsonify({'success': True, 'user_id': user_id, **result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trophies_bp.route('/api/trophies/activity')
@trophies_bp.route('/api/trophie/activity')
def trophy_activity_api():
    """Recent trophy unlocks for the user (Feature 20)."""
    try:
        user_id = _resolve_uid()
        try:
            limit = min(50, max(1, int(request.args.get('limit', 15))))
        except (TypeError, ValueError):
            limit = 15
        from backend.services.trophy_social_service import get_activity
        activities = get_activity(user_id, limit=limit)
        return jsonify({'success': True, 'user_id': user_id, 'activities': activities}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trophies_bp.route('/api/trophies/compare')
@trophies_bp.route('/api/trophie/compare')
def trophy_compare_api():
    """Compare two users' trophy walls (Feature 18)."""
    try:
        user_id = _resolve_uid()
        other = request.args.get('with') or request.args.get('user_b') or ''
        if not other:
            return jsonify({'success': False, 'error': "query param 'with' (other user_id) is required"}), 400
        from backend.services.trophy_social_service import compare_users
        result = compare_users(user_id, other)
        return jsonify({'success': True, **result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trophies_bp.route('/api/trophies/showcase', methods=['GET'])
@trophies_bp.route('/api/trophie/showcase', methods=['GET'])
def get_showcase_api():
    """Get a user's pinned showcase trophies, joined with definitions (Feature 14)."""
    try:
        # Allow viewing another user's showcase (?user_id=) for profile pages
        user_id = request.args.get('user_id') or _resolve_uid()
        from backend.services.trophy_social_service import get_showcase
        ids = get_showcase(user_id)
        defs = _definitions_by_id()
        unlocked = set()
        try:
            from backend.services.trophies_db_service import get_user_trophies
            unlocked = {str(t.get('id')) for t in (get_user_trophies(user_id) or [])}
        except Exception:
            pass
        items = []
        for tid in ids:
            d = defs.get(str(tid))
            if d:
                items.append({**d, 'unlocked': str(tid) in unlocked})
        return jsonify({'success': True, 'user_id': user_id, 'trophy_ids': ids, 'trophies': items}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trophies_bp.route('/api/trophies/showcase', methods=['POST'])
@trophies_bp.route('/api/trophie/showcase', methods=['POST'])
def set_showcase_api():
    """Pin up to 6 trophies to a user's showcase (Feature 14)."""
    try:
        data = request.get_json() or {}
        user_id = _resolve_uid()
        ids = data.get('trophy_ids')
        if ids is None:
            return jsonify({'success': False, 'error': 'trophy_ids (list) is required'}), 400
        if not isinstance(ids, list):
            return jsonify({'success': False, 'error': 'trophy_ids must be a list'}), 400
        # Only allow pinning known trophy ids
        defs = _definitions_by_id()
        ids = [str(x) for x in ids if str(x) in defs]
        from backend.services.trophy_social_service import set_showcase
        saved = set_showcase(user_id, ids)
        return jsonify({'success': True, 'user_id': user_id, 'trophy_ids': saved}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trophies_bp.route('/api/trophies/health')
@trophies_bp.route('/api/trophie/health')
def trophy_health_api():
    """Health check: definitions validity, writable showcase dir, DB tables (Feature 25)."""
    try:
        result = validate_definitions()
        # Writable showcase dir
        showcase_writable = False
        try:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            sc_dir = os.path.join(base, 'data', 'trophy_showcase')
            os.makedirs(sc_dir, exist_ok=True)
            test_path = os.path.join(sc_dir, '.health_check')
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write('ok')
            os.remove(test_path)
            showcase_writable = True
        except OSError:
            showcase_writable = False
        db_tables = False
        try:
            from backend.services.trophies_db_service import trophies_tables_exist
            db_tables = bool(trophies_tables_exist())
        except Exception:
            db_tables = False
        healthy = result['ok'] and showcase_writable
        return jsonify({
            'success': True,
            'healthy': healthy,
            'definitions': result,
            'showcase_writable': showcase_writable,
            'trophy_db_tables': db_tables,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'healthy': False, 'error': str(e)}), 500


# Agent capability map: every UI action has an agent-callable equivalent (Feature 22 / parity)
_AGENT_TOOLS = [
    {'action': 'list', 'method': 'GET', 'path': '/api/trophies/list', 'mutating': False, 'description': 'All trophies + user unlocks.'},
    {'action': 'definitions', 'method': 'GET', 'path': '/api/trophies/definitions', 'mutating': False, 'description': 'Canonical definitions + sets.'},
    {'action': 'quests', 'method': 'GET', 'path': '/api/trophies/quests', 'mutating': False, 'description': 'Daily/weekly quests.'},
    {'action': 'leaderboard', 'method': 'GET', 'path': '/api/trophies/leaderboard', 'mutating': False, 'description': 'Top collectors.'},
    {'action': 'activity', 'method': 'GET', 'path': '/api/trophies/activity', 'mutating': False, 'description': 'Recent unlocks.'},
    {'action': 'compare', 'method': 'GET', 'path': '/api/trophies/compare', 'mutating': False, 'params': ['with'], 'description': 'Compare two users.'},
    {'action': 'showcase_get', 'method': 'GET', 'path': '/api/trophies/showcase', 'mutating': False, 'description': 'Pinned showcase.'},
    {'action': 'health', 'method': 'GET', 'path': '/api/trophies/health', 'mutating': False, 'description': 'Health check.'},
    {'action': 'sync', 'method': 'POST', 'path': '/api/trophies/sync', 'mutating': True, 'description': 'Award all earned trophies.'},
    {'action': 'claim', 'method': 'POST', 'path': '/api/trophies/claim', 'mutating': True, 'params': ['trophy_id'], 'description': 'Claim a trophy reward.'},
    {'action': 'showcase_set', 'method': 'POST', 'path': '/api/trophies/showcase', 'mutating': True, 'params': ['trophy_ids'], 'description': 'Pin up to 6 trophies.'},
]


@trophies_bp.route('/api/trophies/agent-tools')
@trophies_bp.route('/api/trophie/agent-tools')
def trophy_agent_tools_api():
    """Capability map for agents (Feature 22)."""
    return jsonify({'success': True, 'tools': _AGENT_TOOLS,
                    'note': 'Mutating actions via /api/trophies/agent-action require approved=true.'}), 200


@trophies_bp.route('/api/trophies/agent-action', methods=['POST'])
@trophies_bp.route('/api/trophie/agent-action', methods=['POST'])
def trophy_agent_action_api():
    """Execute a trophy action as an agent. Read actions run directly; mutating actions
    require explicit approved=true (parity with the UI, Feature 22)."""
    try:
        data = request.get_json() or {}
        action = data.get('action')
        tool = next((t for t in _AGENT_TOOLS if t['action'] == action), None)
        if not tool:
            return jsonify({'success': False, 'error': 'Unknown action',
                            'available': [t['action'] for t in _AGENT_TOOLS]}), 400
        if tool['mutating'] and not data.get('approved'):
            return jsonify({'success': False, 'error': 'Mutating action requires approved=true',
                            'action': action}), 403
        user_id = _resolve_uid()
        if action == 'list':
            return list_trophies_api()
        if action == 'definitions':
            return trophy_definitions_api()
        if action == 'quests':
            return trophy_quests_api()
        if action == 'leaderboard':
            return trophy_leaderboard_api()
        if action == 'activity':
            return trophy_activity_api()
        if action == 'health':
            return trophy_health_api()
        if action == 'compare':
            from backend.services.trophy_social_service import compare_users
            other = data.get('with') or data.get('user_b') or ''
            if not other:
                return jsonify({'success': False, 'error': "'with' is required"}), 400
            return jsonify({'success': True, **compare_users(user_id, other)}), 200
        if action == 'showcase_get':
            from backend.services.trophy_social_service import get_showcase
            return jsonify({'success': True, 'user_id': user_id, 'trophy_ids': get_showcase(user_id)}), 200
        if action == 'sync':
            return sync_trophies_api()
        if action == 'claim':
            return claim_trophy_api()
        if action == 'showcase_set':
            return set_showcase_api()
        return jsonify({'success': False, 'error': 'Unhandled action'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trophies_bp.route('/api/trophies/admin/upsert', methods=['POST'])
@trophies_bp.route('/api/trophie/admin/upsert', methods=['POST'])
def trophy_admin_upsert_api():
    """Add or update a trophy definition in the JSON source (Feature 25).

    Disabled unless TROPHY_ADMIN_SECRET is set and the X-Trophy-Admin-Token header matches.
    """
    if not _admin_authorized():
        return jsonify({'success': False, 'error': 'Trophy authoring disabled or unauthorized'}), 403
    try:
        body = request.get_json() or {}
        trophy = body.get('trophy')
        if not isinstance(trophy, dict) or not trophy.get('id'):
            return jsonify({'success': False, 'error': "body.trophy with an 'id' is required"}), 400
        data = load_trophy_definitions_file()
        trophies = data.get('trophies', [])
        tid = str(trophy['id'])
        replaced = False
        for i, t in enumerate(trophies):
            if str(t.get('id')) == tid:
                trophies[i] = {**t, **trophy}
                replaced = True
                break
        if not replaced:
            trophies.append(trophy)
        data['trophies'] = trophies
        # Validate the candidate before persisting
        if not save_trophy_definitions_file(data):
            return jsonify({'success': False, 'error': 'Failed to write definitions file'}), 500
        report = validate_definitions()
        return jsonify({'success': True, 'trophy_id': tid, 'action': 'updated' if replaced else 'created',
                        'validation': report}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

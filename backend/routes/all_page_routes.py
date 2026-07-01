"""
All Page Routes
Generic routes for serving HTML pages from project root (static/, index.html, generator/, etc.)
"""
from flask import Blueprint, send_from_directory, redirect, request, render_template, make_response
import os

all_page_bp = Blueprint('all_pages', __name__)

# Version for cache busting - bump on deploy
CONTENT_VERSION = "20260428a"


def _base_path():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _static_dir():
    """Static assets at project root: static/ (merged from former vidgenerator/static)."""
    return os.path.join(_base_path(), 'static')


# Serve static files at /static/ from project root static/ (avoid clash with Flask default 'static' endpoint)
@all_page_bp.route('/static/<path:filename>', endpoint='serve_root_static')
def serve_static(filename):
    from flask import abort
    static_dir = _static_dir()
    if not os.path.isdir(static_dir):
        return abort(404)
    try:
        return send_from_directory(static_dir, filename)
    except Exception:
        return abort(404)




# All pages are registered automatically from this list (create_page_route below).
# Add any new page subdir with index.html at project root here to expose it.
PAGES = [
    'gallery', 'battle', 'shop', 'chat', 'debugger',
    'quests', 'news', 'metal', 'theme-points', 'battlegrounds', 'champions-league',
    'editor', 'monetization', 'milkyway', 'rights-law', 'victory-tech-tree',
    'danish-divine-tech-tree', 'academic-perspective', 'theme_premium',
    'time-achievement-guides', 'beta_testing',
    'advanced_calculator', 'agent_support', 'game', 'generator', 'lab',
    'social', 'profile', 'user', 'trophies',
    'compendium', 'starmap25',
    'aggregator', 'staking-monitor', 'staking-leaderboard', 'staking-teams', 'explorer', 'proof-of-reserves',
    'market', 'exchange', 'casino', 'customers', 'camgirls', 'command-center', 'hosting',
    'wallets',
    'podcast', 'business-control',
]

# Pages removed from PAGES: redirect HTML routes not covered by dashboard_page_routes
_CONSOLIDATED_PROFILE_TABS = {
    'leaderboards': 'leaderboard',
    'unified_dashboard': 'points',
}


def _register_profile_redirects():
    """Register /path -> /profile?tab=... for removed standalone stat pages."""

    def _make_handler(tab: str, name: str):
        def _redirect():
            return redirect(f'/profile?tab={tab}', code=301)

        _redirect.__name__ = name
        return _redirect

    for slug, tab in _CONSOLIDATED_PROFILE_TABS.items():
        safe = slug.replace('-', '_')
        h = _make_handler(tab, f'redirect_{safe}_to_profile')
        all_page_bp.add_url_rule(f'/{slug}', view_func=h, strict_slashes=False)
        all_page_bp.add_url_rule(f'/{slug}/index.html', view_func=h)


_register_profile_redirects()


@all_page_bp.route('/', methods=['GET'])
def root_index():
    """Serve index.html at project root for /."""
    try:
        base_path = _base_path()
        # Prefer root index.html (after move); fallback to legacy vidgenerator/index.html
        for dir_name, file_name in [('', 'index.html'), ('vidgenerator', 'index.html')]:
            page_path = os.path.join(base_path, dir_name, file_name) if dir_name else os.path.join(base_path, file_name)
            if os.path.exists(page_path):
                directory = os.path.join(base_path, dir_name) if dir_name else base_path
                resp = send_from_directory(directory, 'index.html', mimetype='text/html; charset=utf-8')
                resp.headers['Cache-Control'] = 'public, max-age=300, stale-while-revalidate=60'
                resp.headers['ETag'] = CONTENT_VERSION
                resp.headers['X-Content-Version'] = CONTENT_VERSION
                return resp
    except Exception:
        pass
    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>MasterNoder</title></head>'
        '<body><h1>MasterNoder</h1><p><a href="/generator">Generator</a> | '
        '<a href="/gallery">Gallery</a></p></body></html>',
        200,
        {'Content-Type': 'text/html; charset=utf-8'},
    )

def create_page_route(page_name):
    """Create route handlers for a page. Use default arg to capture page_name per handler (closure fix)."""
    _ep = f'page_{page_name}'
    _pn = page_name  # capture for closure

    # Root routes only; /vidgenerator/* redirects handled by vidgenerator_redirect_path
    @all_page_bp.route(f'/{page_name}', methods=['GET'], endpoint=_ep)
    @all_page_bp.route(f'/{page_name}/', methods=['GET'], endpoint=f'{_ep}_slash')
    @all_page_bp.route(f'/{page_name}/index.html', methods=['GET'], endpoint=f'{_ep}_html')
    def page_handler(_page_name=_pn):
        """Generic page handler - _page_name default captures correct page per route."""
        try:
            base_path = _base_path()
            # Handle special cases
            if _page_name == 'theme_premium':
                page_path = os.path.join(base_path, 'theme_premium', 'index.html')
            elif _page_name == 'theme-points':
                page_path = os.path.join(base_path, 'theme-points', 'index.html')
            elif _page_name == 'champions-league':
                page_path = os.path.join(base_path, 'champions-league', 'index.html')
            elif _page_name == 'danish-divine-tech-tree':
                page_path = os.path.join(base_path, 'danish-divine-tech-tree', 'index.html')
            elif _page_name == 'victory-tech-tree':
                page_path = os.path.join(base_path, 'victory-tech-tree', 'index.html')
            elif _page_name == 'academic-perspective':
                page_path = os.path.join(base_path, 'academic-perspective', 'index.html')
            elif _page_name == 'time-achievement-guides':
                page_path = os.path.join(base_path, 'time-achievement-guides', 'index.html')
            elif _page_name == 'beta_testing':
                page_path = os.path.join(base_path, 'beta_testing', 'index.html')
            elif _page_name == 'unified_dashboard':
                page_path = os.path.join(base_path, 'unified_dashboard', 'index.html')
            elif _page_name == 'advanced_calculator':
                page_path = os.path.join(base_path, 'advanced_calculator', 'index.html')
            elif _page_name == 'agent_support':
                page_path = os.path.join(base_path, 'agent_support', 'index.html')
            elif _page_name == 'lab':
                page_path = os.path.join(base_path, 'lab', 'index.html')
            elif _page_name == 'compendium':
                page_path = os.path.join(base_path, 'compendium', 'index.html')
            else:
                page_path = os.path.join(base_path, _page_name, 'index.html')
            
            if os.path.exists(page_path):
                # Stream with send_file for faster TTFB (same as root_index)
                if _page_name in ('theme_premium', 'theme-points', 'champions-league', 'danish-divine-tech-tree',
                                 'victory-tech-tree', 'academic-perspective', 'time-achievement-guides', 'beta_testing',
                                 'unified_dashboard', 'advanced_calculator', 'agent_support', 'lab', 'compendium'):
                    dir_path = os.path.dirname(page_path)
                    resp = send_from_directory(dir_path, 'index.html', mimetype='text/html; charset=utf-8')
                else:
                    resp = send_from_directory(
                        os.path.join(base_path, _page_name),
                        'index.html',
                        mimetype='text/html; charset=utf-8',
                    )
                resp.headers['Cache-Control'] = 'public, max-age=300, stale-while-revalidate=60'
                resp.headers['ETag'] = CONTENT_VERSION
                resp.headers['X-Content-Version'] = CONTENT_VERSION
                return resp
            
            # Fallback HTML
            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_page_name.replace('-', ' ').replace('_', ' ').title()} - MasterNoder</title>
    <link rel="stylesheet" href="/static/css/modern-design-system.css">
    <style>
        body {{ 
            padding: 100px 20px 60px; 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%);
            color: #ffffff;
        }}
        .error-container {{
            max-width: 800px;
            margin: 0 auto;
            text-align: center;
            padding: 40px;
            background: rgba(255, 0, 0, 0.1);
            border-radius: 20px;
            border: 2px solid rgba(255, 0, 0, 0.3);
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>{_page_name.replace('-', ' ').replace('_', ' ').title()} Page Not Found</h1>
        <p>The {_page_name} page file could not be located at: {page_path}</p>
    </div>
</body>
</html>"""
            
            return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
            
        except Exception as e:
            return f"Error loading {_page_name} page: {str(e)}", 500
    
    page_handler.__name__ = f'{_pn}_index'
    return page_handler

# Create routes for all pages
for page in PAGES:
    create_page_route(page)


@all_page_bp.route('/casino', methods=['GET'])
def casino_redirect():
    """Nav and bookmarks often use /casino without a trailing slash."""
    return redirect('/casino/', code=301)


@all_page_bp.route('/casino/', methods=['GET'])
@all_page_bp.route('/casino/index.html', methods=['GET'])
def casino_page():
    """Serve virtual-coins casino page."""
    try:
        base_path = _base_path()
        page_dir = os.path.join(base_path, 'casino')
        if os.path.isfile(os.path.join(page_dir, 'index.html')):
            resp = send_from_directory(page_dir, 'index.html', mimetype='text/html; charset=utf-8')
            resp.headers['Cache-Control'] = 'public, max-age=300, stale-while-revalidate=60'
            resp.headers['ETag'] = CONTENT_VERSION
            resp.headers['X-Content-Version'] = CONTENT_VERSION
            return resp
    except Exception as exc:
        return f'Error loading casino page: {exc}', 500
    return 'Casino page not found', 404


@all_page_bp.route('/casino/manifest.webmanifest', methods=['GET'])
def casino_manifest():
    """PWA manifest for casino (Play TWA + installable web app)."""
    try:
        base_path = _base_path()
        page_dir = os.path.join(base_path, 'casino')
        if os.path.isfile(os.path.join(page_dir, 'manifest.webmanifest')):
            resp = send_from_directory(
                page_dir,
                'manifest.webmanifest',
                mimetype='application/manifest+json; charset=utf-8',
            )
            resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=300'
            return resp
    except Exception:
        pass
    return 'Manifest not found', 404


@all_page_bp.route('/.well-known/assetlinks.json', methods=['GET'])
def well_known_assetlinks():
    """Android Digital Asset Links for TWA / App Links."""
    try:
        static_dir = _static_dir()
        path = os.path.join(static_dir, '.well-known', 'assetlinks.json')
        if os.path.isfile(path):
            resp = send_from_directory(
                os.path.join(static_dir, '.well-known'),
                'assetlinks.json',
                mimetype='application/json; charset=utf-8',
            )
            resp.headers['Cache-Control'] = 'public, max-age=3600'
            return resp
    except Exception:
        pass
    return 'Not found', 404


@all_page_bp.route('/.well-known/apple-app-site-association', methods=['GET'])
def well_known_aasa():
    """Apple Universal Links association file (no file extension)."""
    try:
        static_dir = _static_dir()
        path = os.path.join(static_dir, '.well-known', 'apple-app-site-association')
        if os.path.isfile(path):
            resp = send_from_directory(
                os.path.join(static_dir, '.well-known'),
                'apple-app-site-association',
                mimetype='application/json; charset=utf-8',
            )
            resp.headers['Cache-Control'] = 'public, max-age=3600'
            return resp
    except Exception:
        pass
    return 'Not found', 404


@all_page_bp.route('/debugger/flask', methods=['GET'], endpoint='debugger_flask_template')
@all_page_bp.route('/debugger/flask/', methods=['GET'], endpoint='debugger_flask_template_slash')
def debugger_from_flask_template():
    """
    Same Production Debugger UI as /debugger, served via Flask's template loader
    (backend/templates/debugger/index.html — kept in sync with root debugger/index.html).
    """
    try:
        body = render_template('debugger/index.html')
        resp = make_response(body)
        resp.headers['Content-Type'] = 'text/html; charset=utf-8'
        resp.headers['Cache-Control'] = 'public, max-age=120, stale-while-revalidate=60'
        resp.headers['ETag'] = CONTENT_VERSION
        resp.headers['X-Content-Version'] = CONTENT_VERSION
        resp.headers['X-Debugger-Served'] = 'flask-template'
        return resp
    except Exception as e:
        base_path = _base_path()
        fb_dir = os.path.join(base_path, 'debugger')
        fb_file = os.path.join(fb_dir, 'index.html')
        if os.path.isfile(fb_file):
            resp = send_from_directory(fb_dir, 'index.html', mimetype='text/html; charset=utf-8')
            resp.headers['X-Debugger-Served'] = 'static-fallback'
            return resp
        return f'<!DOCTYPE html><html><body><pre>Debugger template error: {e!s}</pre></body></html>', 500, {
            'Content-Type': 'text/html; charset=utf-8',
        }


# Compendium (Rulebook V2.1) — page-1.html through page-10.html
def _compendium_gate(page_number: int):
    """Redirect to library paywall when premium page is locked."""
    if not page_number or page_number <= 3:
        return None
    try:
        from backend.services.account_resolution_service import resolve_user_id
        from backend.services.compendium_access_service import can_access_page

        uid = resolve_user_id(from_body=False, from_query=True)
        if not can_access_page(uid, page_number):
            return redirect(f"/compendium/?locked={page_number}", code=302)
    except Exception:
        pass
    return None


@all_page_bp.route('/compendium/page-<int:n>.html', methods=['GET'])
@all_page_bp.route('/compendium/page-<int:n>', methods=['GET'])
def compendium_page(n):
    if n < 1 or n > 10:
        return "Invalid compendium page", 404
    blocked = _compendium_gate(n)
    if blocked:
        return blocked
    try:
        base_path = _base_path()
        page_path = os.path.join(base_path, 'compendium', f'page-{n}.html')
        if os.path.exists(page_path):
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
            headers = {
                'Content-Type': 'text/html; charset=utf-8',
                'Cache-Control': 'public, max-age=300, stale-while-revalidate=60',
                'ETag': CONTENT_VERSION,
                'X-Content-Version': CONTENT_VERSION,
            }
            return content, 200, headers
    except Exception:
        pass
    return "Page not found", 404


def _serve_compendium_rulebook_viewer_html():
    """Serve shared rulebook-viewer.html (same shell for v1, v4–v16, v3-2)."""
    try:
        base_path = _base_path()
        page_path = os.path.join(base_path, 'compendium', 'rulebook-viewer.html')
        if os.path.exists(page_path):
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
            headers = {
                'Content-Type': 'text/html; charset=utf-8',
                'Cache-Control': 'public, max-age=300, stale-while-revalidate=60',
                'ETag': CONTENT_VERSION,
                'X-Content-Version': CONTENT_VERSION,
            }
            return content, 200, headers
    except Exception:
        pass
    return None


@all_page_bp.route('/compendium/rulebook-v3-2.html', methods=['GET'])
@all_page_bp.route('/compendium/rulebook-v3-2', methods=['GET'])
def compendium_rulebook_v3_2():
    """V3.2 systemic protocols — URL uses hyphen; API id is v3.2."""
    out = _serve_compendium_rulebook_viewer_html()
    if out:
        return out
    return "Page not found", 404


@all_page_bp.route('/compendium/rulebook-v<int:n>.html', methods=['GET'])
@all_page_bp.route('/compendium/rulebook-v<int:n>', methods=['GET'])
def compendium_rulebook_version(n):
    """Serve rulebook viewer for V1–V16."""
    if n < 1 or n > 16:
        return "Invalid rulebook version", 404
    from backend.services.compendium_access_service import RULEBOOK_PAGE_MAP

    page_num = RULEBOOK_PAGE_MAP.get(n)
    blocked = _compendium_gate(page_num) if page_num else None
    if blocked:
        return blocked
    out = _serve_compendium_rulebook_viewer_html()
    if out:
        return out
    return "Page not found", 404


@all_page_bp.route('/compendium/hunters-rulebook.html', methods=['GET'])
@all_page_bp.route('/compendium/hunters-rulebook', methods=['GET'])
def compendium_hunters_rulebook():
    """Serve Hunters Rulebook (Part II of unified compendium)."""
    blocked = _compendium_gate(11)
    if blocked:
        return blocked
    try:
        base_path = _base_path()
        page_path = os.path.join(base_path, 'compendium', 'hunters-rulebook.html')
        if os.path.exists(page_path):
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
            headers = {
                'Content-Type': 'text/html; charset=utf-8',
                'Cache-Control': 'public, max-age=300, stale-while-revalidate=60',
                'ETag': CONTENT_VERSION,
                'X-Content-Version': CONTENT_VERSION,
            }
            return content, 200, headers
    except Exception:
        pass
    return "Page not found", 404


# Nested path: dashboard/master_control
@all_page_bp.route('/dashboard/master_control', methods=['GET'])
@all_page_bp.route('/dashboard/master_control/', methods=['GET'])
@all_page_bp.route('/dashboard/master_control/index.html', methods=['GET'])
def dashboard_master_control():
    """Serve dashboard/master_control/index.html at project root."""
    try:
        base_path = _base_path()
        page_path = os.path.join(base_path, 'dashboard', 'master_control', 'index.html')
        if os.path.exists(page_path):
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
            headers = {
                'Content-Type': 'text/html; charset=utf-8',
                'Cache-Control': 'public, max-age=300, stale-while-revalidate=60',
                'ETag': CONTENT_VERSION,
                'X-Content-Version': CONTENT_VERSION,
            }
            return content, 200, headers
    except Exception:
        pass
    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Master Control - Not Found</title></head>'
        '<body><h1>Master Control</h1><p>Page file not found.</p></body></html>',
        200,
        {'Content-Type': 'text/html; charset=utf-8'},
    )


@all_page_bp.route('/dashboard/agents_control', methods=['GET'])
@all_page_bp.route('/dashboard/agents_control/', methods=['GET'])
@all_page_bp.route('/dashboard/agents_control/index.html', methods=['GET'])
def dashboard_agents_control():
    """Serve dashboard/agents_control/index.html."""
    try:
        base_path = _base_path()
        page_path = os.path.join(base_path, 'dashboard', 'agents_control', 'index.html')
        if os.path.exists(page_path):
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/html; charset=utf-8', 'X-Content-Version': CONTENT_VERSION}
    except Exception:
        pass
    return '<html><body><h1>Agents Control</h1><p>Not found</p></body></html>', 404


# Agents page — dedicated route to avoid endpoint-naming conflicts with create_page_route loop
@all_page_bp.route('/agents', methods=['GET'])
@all_page_bp.route('/agents/', methods=['GET'])
@all_page_bp.route('/agents/index.html', methods=['GET'])
def agents_page():
    """Serve agents/index.html at project root."""
    try:
        base_path = _base_path()
        page_path = os.path.join(base_path, 'agents', 'index.html')
        if os.path.exists(page_path):
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {
                'Content-Type': 'text/html; charset=utf-8',
                'Cache-Control': 'public, max-age=300, stale-while-revalidate=60',
                'ETag': CONTENT_VERSION,
                'X-Content-Version': CONTENT_VERSION,
            }
    except Exception as e:
        return f"Error loading agents page: {str(e)}", 500
    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Agents - MasterNoder</title></head>'
        '<body><h1>Agent Report</h1><p>Page file not found.</p></body></html>',
        200,
        {'Content-Type': 'text/html; charset=utf-8'},
    )


# --- SEO: sitemap + robots ---
_SITEMAP_PATHS = (
    '/',
    '/generator/',
    '/camgirls/',
    '/exchange/',
    '/casino/',
    '/hosting/',
    '/shop/',
    '/game/',
    '/explorer/',
    '/compendium/',
    '/profile/',
)


@all_page_bp.route('/robots.txt', methods=['GET'])
def robots_txt():
    base = (os.environ.get('BASE_URL') or 'https://masternoder.dk').rstrip('/')
    body = '\n'.join([
        'User-agent: *',
        'Allow: /',
        '',
        f'Sitemap: {base}/sitemap.xml',
        '',
    ])
    resp = make_response(body, 200)
    resp.headers['Content-Type'] = 'text/plain; charset=utf-8'
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp


@all_page_bp.route('/sitemap.xml', methods=['GET'])
def sitemap_xml():
    base = (os.environ.get('BASE_URL') or 'https://masternoder.dk').rstrip('/')
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in _SITEMAP_PATHS:
        loc = base + (path if path != '/' else '/')
        priority = '1.0' if path == '/' else ('0.9' if path in ('/hosting/', '/generator/', '/camgirls/', '/exchange/', '/casino/') else '0.7')
        lines.append('  <url>')
        lines.append(f'    <loc>{loc}</loc>')
        lines.append(f'    <changefreq>weekly</changefreq>')
        lines.append(f'    <priority>{priority}</priority>')
        lines.append('  </url>')
    lines.append('</urlset>')
    body = '\n'.join(lines)
    resp = make_response(body, 200)
    resp.headers['Content-Type'] = 'application/xml; charset=utf-8'
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp


# --- /vidgenerator redirects (301 to root) ---
@all_page_bp.route('/vidgenerator', methods=['GET'])
def vidgenerator_redirect_root():
    """Redirect /vidgenerator to / (primary site)."""
    return redirect('/', code=301)


@all_page_bp.route('/vidgenerator/', methods=['GET'])
def vidgenerator_redirect_slash():
    """Redirect /vidgenerator/ to /."""
    return redirect('/', code=301)


@all_page_bp.route('/vidgenerator/static/<path:filename>', methods=['GET'])
def vidgenerator_redirect_static(filename):
    """Redirect /vidgenerator/static/* to /static/*."""
    return redirect(f'/static/{filename}', code=301)


@all_page_bp.route('/vidgenerator/<path:subpath>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def vidgenerator_redirect_path(subpath):
    """Redirect /vidgenerator/<path> to /<path>. Use 308 for api/ so method (POST etc.) is preserved."""
    target = '/' + subpath.rstrip('/')
    if subpath.endswith('/'):
        target = target + '/'
    qs = request.query_string.decode('utf-8') if request.query_string else ''
    if qs:
        target = target + ('?' + qs)
    # 308 preserves request method (POST stays POST); 301 can turn POST into GET in some clients
    code = 308 if subpath.startswith('api/') else 301
    return redirect(target, code=code)

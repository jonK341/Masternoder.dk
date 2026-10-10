"""Home page routes"""
from flask import render_template, request, make_response
import os


def register_home_routes(app):
    """Register home page routes"""
    
    # Register /vidgenerator routes FIRST (before legacy routes)
    # Use strict_slashes=False to handle both with and without trailing slash
    # Also register without prefix for nginx rewrite compatibility
    @app.route('/vidgenerator', methods=['GET', 'POST'], endpoint='home_vidgenerator', strict_slashes=False)
    @app.route('/vidgenerator/', methods=['GET', 'POST'], endpoint='home_vidgenerator_slash')
    @app.route('/vidgenerator/home', methods=['GET', 'POST'], endpoint='home_vidgenerator_home')
    @app.route('/', methods=['GET', 'POST'], endpoint='home_root')
    def home():
        """Home page - shows links to all modules"""
        try:
            # Always show new home.html for /vidgenerator paths
            import time
            import random
            version = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
            # Force template reload by clearing Jinja cache
            from flask import current_app
            if hasattr(current_app, 'jinja_env'):
                current_app.jinja_env.cache.clear()
            response = make_response(render_template('home.html', page_version=version))
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private, proxy-revalidate, no-transform'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
            response.headers['X-Content-Version'] = version
            response.headers['X-Timestamp'] = str(time.time())
            # Add unique ETag based on version to prevent conditional requests
            # Add ETag for cache validation (but still no-cache)
            response.headers['ETag'] = f'"{version}"'
            response.headers['Vary'] = 'Accept-Encoding'
            return response
        except Exception as e:
            # If template fails, log error but return a working page with correct links
            import traceback
            error_msg = traceback.format_exc()
            print(f"ERROR rendering home.html: {e}")
            print(error_msg)
            # Return a fallback page with correct generator link
            return f"""
            <!DOCTYPE html>
            <html>
            <head><title>Error Loading Template</title></head>
            <body>
                <h1>Error Loading Template</h1>
                <p>Template 'home.html' not found or error: {str(e)}</p>
                <p><a href="/vidgenerator/generator">Go to Generator</a></p>
                <pre>{error_msg[:500]}</pre>
            </body>
            </html>
            """, 500, {'Content-Type': 'text/html; charset=utf-8'}
    
    @app.route('/debug-report')
    @app.route('/vidgenerator/debug-report')
    def debug_report():
        """Enhanced debug report page with logging"""
        # Try to read enhanced version first, then fallback
        enhanced_file = '/var/www/html/vidgenerator/enhanced_debug_report.html'
        debug_file = '/var/www/html/vidgenerator/create_debug_report.html'
        
        try:
            if os.path.exists(enhanced_file):
                with open(enhanced_file, 'r', encoding='utf-8') as f:
                    html = f.read()
            elif os.path.exists(debug_file):
                with open(debug_file, 'r', encoding='utf-8') as f:
                    html = f.read()
            else:
                # Return simple embedded version
                html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Debug Report</title>
<style>body{font-family:monospace;background:#1a1a1a;color:#00ff00;padding:20px}
.test-section{background:#2a2a2a;border:1px solid #00ff00;padding:15px;margin:10px 0}
.pass{color:#00ff00}.fail{color:#ff0000}.info{color:#ffff00}
button{background:#00ff00;color:#000;border:none;padding:10px 20px;cursor:pointer;margin:5px}
button:hover{background:#00cc00}pre{background:#000;padding:10px;overflow-x:auto}</style></head>
<body><h1>🔍 Client-Server Debug Report</h1>
<div class="test-section"><h2>1. Page Load Test</h2><button onclick="testPageLoad()">Test</button><div id="page-load-result"></div></div>
<div class="test-section"><h2>2. JavaScript Files</h2><button onclick="testJSFiles()">Test</button><div id="js-files-result"></div></div>
<div class="test-section"><h2>3. API Endpoints</h2><button onclick="testAPIEndpoints()">Test</button><div id="api-result"></div></div>
<div class="test-section"><h2>4. Cache Headers</h2><button onclick="testCacheHeaders()">Test</button><div id="cache-headers-result"></div></div>
<div class="test-section"><h2>5. Service Worker</h2><button onclick="testServiceWorker()">Test</button><div id="sw-result"></div></div>
<div class="test-section"><h2>6. Run All</h2><button onclick="runAllTests()">Run All</button><div id="all-results"></div></div>
<script>
const BASE_URL=window.location.origin;
async function testPageLoad(){const r=document.getElementById('page-load-result');r.innerHTML='<p class="info">Testing...</p>';
try{const res=await fetch(`${BASE_URL}/vidgenerator`);const h=await res.text();
const c={'Has page_version':h.includes('page_version'),'Has script tags':(h.match(/<script/g)||[]).length>0,'Response OK':res.ok,'Cache-Control':res.headers.get('cache-control')};
let o='<pre>';for(const[k,v]of Object.entries(c)){const s=v?'pass':'fail';o+=`<span class="${s}">${v?'✓':'✗'} ${k}: ${v}</span>\\n`}o+='</pre>';r.innerHTML=o}catch(e){r.innerHTML=`<p class="fail">Error: ${e.message}</p>`}}
async function testJSFiles(){const r=document.getElementById('js-files-result');r.innerHTML='<p class="info">Testing...</p>';
const f=['/vidgenerator/static/js/main.js','/vidgenerator/static/js/generator/theme-selector.js'];
let o='<pre>';for(const file of f){try{const res=await fetch(`${BASE_URL}${file}`);const s=res.ok?'pass':'fail';o+=`<span class="${s}">${res.ok?'✓':'✗'} ${file}: ${res.status}</span>\\n`}catch(e){o+=`<span class="fail">✗ ${file}: ${e.message}</span>\\n`}}o+='</pre>';r.innerHTML=o}
async function testAPIEndpoints(){const r=document.getElementById('api-result');r.innerHTML='<p class="info">Testing...</p>';
const e=['/vidgenerator/api/points/all','/vidgenerator/api/points/chat'];
let o='<pre>';for(const ep of e){try{const res=await fetch(`${BASE_URL}${ep}`);const s=res.ok?'pass':'fail';o+=`<span class="${s}">${res.ok?'✓':'✗'} ${ep}: ${res.status}</span>\\n`}catch(e){o+=`<span class="fail">✗ ${ep}: ${e.message}</span>\\n`}}o+='</pre>';r.innerHTML=o}
async function testCacheHeaders(){const r=document.getElementById('cache-headers-result');r.innerHTML='<p class="info">Testing...</p>';
try{const res=await fetch(`${BASE_URL}/vidgenerator`);const h={'Cache-Control':res.headers.get('cache-control'),'X-Content-Version':res.headers.get('x-content-version')};
let o='<pre>';for(const[k,v]of Object.entries(h)){const hv=v&&v!=='null';const s=hv?'pass':'fail';o+=`<span class="${s}">${hv?'✓':'✗'} ${k}: ${v||'missing'}</span>\\n`}o+='</pre>';r.innerHTML=o}catch(e){r.innerHTML=`<p class="fail">Error: ${e.message}</p>`}}
async function testServiceWorker(){const r=document.getElementById('sw-result');r.innerHTML='<p class="info">Testing...</p>';
if('serviceWorker' in navigator){try{const regs=await navigator.serviceWorker.getRegistrations();
let o='<pre>';o+=`<span class="info">Found ${regs.length} registrations</span>\\n`;
if(regs.length===0){o+=`<span class="pass">✓ No service workers (expected)</span>\\n`}else{o+=`<span class="fail">✗ Service workers still registered</span>\\n`}o+='</pre>';r.innerHTML=o}catch(e){r.innerHTML=`<p class="fail">Error: ${e.message}</p>`}}else{r.innerHTML='<p class="info">SW not supported</p>'}}
async function runAllTests(){const r=document.getElementById('all-results');r.innerHTML='<p class="info">Running...</p>';
await testPageLoad();await testJSFiles();await testAPIEndpoints();await testCacheHeaders();await testServiceWorker();
r.innerHTML='<p class="pass">All tests completed!</p>'}
</script></body></html>"""
        except Exception:
            html = """<!DOCTYPE html><html><head><title>Debug Report</title></head>
<body><h1>Debug Report</h1><p>Error loading debug report.</p></body></html>"""
        
        response = make_response(html)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        return response
    
    @app.route('/')
    @app.route('/vidgenerator')
    def home():
        """Enhanced home page with navigation and features"""
        try:
            # Try to render enhanced home template
            enhanced_template = '/var/www/html/vidgenerator/src/web/templates/home_enhanced.html'
            if os.path.exists(enhanced_template):
                with open(enhanced_template, 'r', encoding='utf-8') as f:
                    html = f.read()
                response = make_response(html)
                response.headers['Content-Type'] = 'text/html; charset=utf-8'
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                return response
            else:
                # Fallback to regular template
                return render_template('home.html')
        except Exception as e:
            # Ultimate fallback
            return render_template('home.html')
    
    @app.route('/old-root')
    def root():
        """Root path - show simple welcome page (backward compatibility)"""
        # Use the new improved landing page template
        try:
            return render_template('landing_masternoder.html')
        except Exception as e:
            # Fallback if template not found
            import traceback
            print(f"Error rendering landing_masternoder.html: {e}")
            print(traceback.format_exc())
            return """
                <!DOCTYPE html>
                <html lang="da">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Masternoder.dk - Hovedside</title>
                    <style>
                        * { margin: 0; padding: 0; box-sizing: border-box; }
                        body { 
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            min-height: 100vh;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            padding: 20px;
                        }
                        .container { 
                            max-width: 900px; 
                            width: 100%;
                            background: white; 
                            padding: 60px 40px; 
                            border-radius: 20px; 
                            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                            text-align: center;
                        }
                        h1 { 
                            color: #667eea; 
                            font-size: 3em;
                            margin-bottom: 20px;
                            font-weight: 700;
                        }
                        .subtitle {
                            color: #666;
                            font-size: 1.3em;
                            margin-bottom: 40px;
                            line-height: 1.6;
                        }
                        .link { 
                            display: inline-block; 
                            margin: 10px;
                            padding: 18px 40px; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white; 
                            text-decoration: none; 
                            border-radius: 50px; 
                            font-weight: 600;
                            font-size: 1.1em;
                            transition: transform 0.3s, box-shadow 0.3s;
                            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
                        }
                        .link:hover { 
                            transform: translateY(-3px);
                            box-shadow: 0 8px 30px rgba(102, 126, 234, 0.5);
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>🎬 Velkommen til Masternoder.dk</h1>
                        <p class="subtitle">Din platform for AI-drevet videogenerering</p>
                        <a href="/vidgenerator/generator" class="link">🚀 Gå til Platform</a>
                    </div>
                </body>
                </html>
                """, 200, {'Content-Type': 'text/html; charset=utf-8'}


"""Root landing page for masternoder.dk"""
from flask import render_template, make_response, request
import time
import random

def register_root_landing_routes(app):
    """Register root landing page routes for masternoder.dk"""
    
    # Register /fresh route - multiple paths to ensure it works
    @app.route('/fresh', methods=['GET'], endpoint='root_landing_fresh', strict_slashes=False)
    @app.route('/fresh/', methods=['GET'], endpoint='root_landing_fresh_slash', strict_slashes=False)
    @app.route('/vidgenerator/fresh', methods=['GET'], endpoint='root_landing_fresh_vidgenerator', strict_slashes=False)
    @app.route('/vidgenerator/fresh/', methods=['GET'], endpoint='root_landing_fresh_vidgenerator_slash', strict_slashes=False)
    def root_landing_fresh():
        """Fresh landing page for masternoder.dk"""
        try:
            version = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
            # Force template reload
            from flask import current_app
            if hasattr(current_app, 'jinja_env'):
                current_app.jinja_env.cache.clear()
            
            response = make_response(render_template('landing_fresh.html', page_version=version))
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        except Exception as e:
            import traceback
            print(f"Error rendering landing_fresh.html: {e}")
            print(traceback.format_exc())
            # Fallback HTML
            return f"""
            <!DOCTYPE html>
            <html lang="da">
            <head>
                <meta charset="UTF-8">
                <title>MasterNoder.dk - Fresh Landing</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
                        color: #00ff00;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        margin: 0;
                        padding: 20px;
                    }}
                    .container {{
                        text-align: center;
                        padding: 40px;
                        background: rgba(10, 10, 10, 0.9);
                        border-radius: 20px;
                        border: 2px solid rgba(0, 255, 0, 0.3);
                    }}
                    h1 {{
                        font-size: 3em;
                        margin-bottom: 20px;
                        text-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
                    }}
                    .error {{
                        color: #ff4444;
                        margin: 20px 0;
                    }}
                    .link {{
                        display: inline-block;
                        margin: 20px;
                        padding: 20px 50px;
                        background: linear-gradient(135deg, #00ff00, #00cc00);
                        color: #000;
                        text-decoration: none;
                        border-radius: 50px;
                        font-weight: 700;
                        font-size: 1.3em;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎬 MasterNoder.dk</h1>
                    <p class="error">Error loading fresh landing page: {e}</p>
                    <p>Traceback: {traceback.format_exc()[:500]}</p>
                    <a href="/vidgenerator/generator/simple" class="link">🚀 Go to Generator</a>
                    <a href="/" class="link">🏠 Home</a>
                </div>
            </body>
            </html>
            """, 200, {'Content-Type': 'text/html; charset=utf-8'}
    
    @app.route('/', methods=['GET'], endpoint='root_landing')
    def root_landing():
        """Root landing page for masternoder.dk"""
        try:
            version = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
            # Check for fresh parameter
            use_fresh = request.args.get('fresh', 'false').lower() == 'true'
            
            # Use fresh landing page if requested, otherwise try beautiful, then fallback
            try:
                if use_fresh:
                    response = make_response(render_template('landing_fresh.html', page_version=version))
                else:
                    response = make_response(render_template('landing_beautiful.html', page_version=version))
            except:
                # Fallback to index_masternoder
                response = make_response(render_template('index_masternoder.html', page_version=version))
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        except Exception as e:
            # Fallback if template not found
            import traceback
            print(f"Error rendering index_masternoder.html: {e}")
            print(traceback.format_exc())
            return f"""
            <!DOCTYPE html>
            <html lang="da">
            <head>
                <meta charset="UTF-8">
                <title>MasterNoder.dk</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
                        color: #00ff00;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        margin: 0;
                    }}
                    .container {{
                        text-align: center;
                        padding: 40px;
                        background: rgba(10, 10, 10, 0.9);
                        border-radius: 20px;
                        border: 2px solid rgba(0, 255, 0, 0.3);
                    }}
                    h1 {{
                        font-size: 3em;
                        margin-bottom: 20px;
                        text-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
                    }}
                    .link {{
                        display: inline-block;
                        margin: 20px;
                        padding: 20px 50px;
                        background: linear-gradient(135deg, #00ff00, #00cc00);
                        color: #000;
                        text-decoration: none;
                        border-radius: 50px;
                        font-weight: 700;
                        font-size: 1.3em;
                        transition: transform 0.3s;
                    }}
                    .link:hover {{
                        transform: scale(1.05);
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎬 MasterNoder.dk</h1>
                    <p style="font-size: 1.3em; margin-bottom: 30px;">AI-Drevet Videogenerering Platform</p>
                    <a href="/vidgenerator/generator" class="link">🚀 Start Video Generator</a>
                </div>
            </body>
            </html>
            """, 200, {'Content-Type': 'text/html; charset=utf-8'}


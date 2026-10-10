"""Chat routes"""
from flask import render_template, make_response


def register_chat_routes(app):
    """Register chat routes"""
    
    @app.route('/vidgenerator/chat')
    @app.route('/vidgenerator/chat/')
    # Check if route already registered
    @app.route('/chat')
    def chat_index():
        """Chat room page"""
        try:
            response = make_response(render_template('chat/index.html'))
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        except Exception as e:
            return f"Error loading chat: {e}", 500


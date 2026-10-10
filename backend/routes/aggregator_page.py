"""
Aggregator Dashboard Page Route
"""
from flask import Blueprint, Response, make_response, render_template
import os
import sys

aggregator_page_bp = Blueprint('aggregator_page', __name__)


@aggregator_page_bp.route('/aggregator', methods=['GET'])
@aggregator_page_bp.route('/aggregator/', methods=['GET'])
def aggregator_index():
    """Aggregator dashboard page - serves from vidgenerator/aggregator/index.html file"""
    # Primary path - production
    index_file = '/var/www/html/vidgenerator/vidgenerator/aggregator/index.html'
    
    try:
        if os.path.exists(index_file):
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                response = Response(content, mimetype='text/html; charset=utf-8')
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
            except Exception as read_error:
                print(f"[Aggregator Page] File read error: {read_error}", file=sys.stderr, flush=True)
                return Response(f'Error reading file: {str(read_error)}', status=500, mimetype='text/plain')
        
        # Try template rendering as fallback
        try:
            response = make_response(render_template('aggregator/index.html'))
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        except Exception as template_error:
            print(f"[Aggregator Page] Template error: {template_error}", file=sys.stderr, flush=True)
        
        # Final fallback
        return Response('Aggregator page not found', status=404, mimetype='text/plain')
        
    except Exception as e:
        error_msg = f'Error loading aggregator page: {str(e)}'
        print(f"[Aggregator Page] {error_msg}", file=sys.stderr, flush=True)
        try:
            import traceback
            traceback.print_exc(file=sys.stderr)
        except:
            pass
        return Response(error_msg, status=500, mimetype='text/plain')


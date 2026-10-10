"""
API Routes - External API Endpoints
"""

from flask import jsonify, request
from .. import api_bp
import os
from datetime import datetime

@api_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'documentary-generator',
        'version': '3.21.0-sidebars-tabs'
    })

@api_bp.route('/external-apis/status')
def external_apis_status():
    """Check status of external API integrations"""
    try:
        from src.services.external_apis import FakeNewsDetector
        
        # Check if services are available
        detector = FakeNewsDetector()
        fake_news_ready = detector.initialized
    except:
        fake_news_ready = False
    
    try:
        from src.services.external_apis import SeaGOATService
        seagoat = SeaGOATService()
        seagoat_ready = seagoat.seagoat_installed
    except:
        seagoat_ready = False
    
    # Check API keys from environment
    hypertxt_key = bool(os.getenv('HYPERTXT_API_KEY'))
    vertech_key = bool(os.getenv('VERTECH_ACADEMY_API_KEY'))
    
    return jsonify({
        'seagoat': {
            'installed': seagoat_ready,
            'status': 'ready' if seagoat_ready else 'pending',
            'api_key_required': False
        },
        'fake_news_detector': {
            'installed': True,
            'status': 'ready' if fake_news_ready else 'loading',
            'api_key_required': False
        },
        'hedy': {
            'installed': False,
            'status': 'pending',
            'api_key_required': False
        },
        'hypertxt': {
            'api_key': hypertxt_key,
            'status': 'ready' if hypertxt_key else 'pending',
            'api_key_required': True
        },
        'vertech_academy': {
            'api_key': vertech_key,
            'status': 'ready' if vertech_key else 'pending',
            'api_key_required': True
        }
    })

@api_bp.route('/external-apis/fake-news/detect', methods=['POST'])
def detect_fake_news():
    """Detect fake news in text"""
    try:
        from src.services.external_apis import FakeNewsDetector
        
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text parameter'}), 400
        
        detector = FakeNewsDetector()
        result = detector.detect(data['text'])
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/external-apis/seagoat/search', methods=['POST'])
def seagoat_search():
    """Search code using SeaGOAT"""
    try:
        from src.services.external_apis import SeaGOATService
        
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Missing query parameter'}), 400
        
        repo_path = data.get('repo_path', os.getcwd())
        limit = data.get('limit', 10)
        
        seagoat = SeaGOATService(repo_path=repo_path)
        results = seagoat.search(data['query'], limit=limit)
        
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


"""
Signal Processor Middleware
Automatically processes INVOKE messages and other signals.
In production (PRODUCTION=true or DISABLE_PATH_CORRECTION=1), path correction
is skipped to avoid worker death from recursion/OOM (migration plan Phase 1).
"""
import os
from flask import request, jsonify, g
import re

def _path_correction_enabled():
    """Path correction runs only when not in production and not explicitly disabled."""
    if os.environ.get("PRODUCTION", "").lower() == "true":
        return False
    if os.environ.get("DISABLE_PATH_CORRECTION", "") == "1":
        return False
    if os.environ.get("FLASK_ENV", "").lower() == "production":
        return False
    return True

def process_invoke_in_request():
    """Process INVOKE messages in incoming requests"""
    # Check request body for INVOKE messages
    if request.is_json:
        data = request.get_json() or {}
        
        # Check for INVOKE in message field
        message = data.get('message', '')
        if message and 'INVOKE' in message.upper():
            try:
                from backend.services.signal_collector import signal_collector
                signal = signal_collector.process_invoke_message(message)
                
                # Add signal info to request context
                if not hasattr(request, 'signal_info'):
                    request.signal_info = {}
                request.signal_info['invoke_signal'] = signal
                
            except Exception as e:
                print(f"Error processing INVOKE message: {e}")
    
    # Check query parameters for INVOKE
    if request.args:
        for key, value in request.args.items():
            if 'invoke' in key.lower() and isinstance(value, str) and 'INVOKE' in value.upper():
                try:
                    from backend.services.signal_collector import signal_collector
                    signal = signal_collector.process_invoke_message(value)
                    
                    if not hasattr(request, 'signal_info'):
                        request.signal_info = {}
                    request.signal_info['invoke_signal'] = signal
                    
                except Exception as e:
                    print(f"Error processing INVOKE in query: {e}")

# Paths that never need correction; skip path_corrector (avoids AI path correction / recursion on health checks)
_SKIP_PATH_CORRECTION = {'/api/health', '/api/version'}


def correct_paths_in_request():
    """Correct paths in incoming requests"""
    if request.path in _SKIP_PATH_CORRECTION:
        return
    try:
        from backend.services.path_corrector import path_corrector
        
        # Correct the request path
        original_path = request.path
        corrected_path, correction_info = path_corrector.correct_path(
            original_path,
            context={
                'method': request.method,
                'endpoint': request.endpoint,
                'expected_type': 'api' if '/api/' in original_path else 'page'
            }
        )
        
        # If path was corrected, update request
        if corrected_path != original_path:
            if not hasattr(request, 'path_correction'):
                request.path_correction = {}
            request.path_correction = {
                'original': original_path,
                'corrected': corrected_path,
                'info': correction_info
            }
            
            # Note: Flask doesn't allow changing request.path directly,
            # but we can store the correction for use in routes
            
    except Exception as e:
        if "recursion" not in str(e).lower():
            print(f"Error correcting path: {e}")

def register_signal_processor_middleware(app):
    """Register signal processor middleware with Flask app.
    In production, correct_paths_in_request is skipped (env PRODUCTION=true or DISABLE_PATH_CORRECTION=1).
    """
    path_correction_enabled = _path_correction_enabled()

    @app.before_request
    def before_request():
        if getattr(g, "skip_api_middleware", False):
            return
        if '/api/' not in request.path:
            return
        process_invoke_in_request()
        if path_correction_enabled:
            correct_paths_in_request()

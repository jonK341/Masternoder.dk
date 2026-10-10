"""
API Module - External API Integrations
Provides API endpoints for external services
"""

from flask import Blueprint

# Create blueprint first
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import routes after blueprint creation to avoid circular imports
# Use try/except to handle import errors gracefully
try:
    from .routes import *
except ImportError as e:
    import sys
    print(f"WARNING: Could not import API routes: {e}", file=sys.stderr)
    # Continue without routes - blueprint will still be registered


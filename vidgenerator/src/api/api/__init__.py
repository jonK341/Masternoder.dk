"""
API Module - External API Integrations
Provides API endpoints for external services
"""

from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import routes after blueprint creation to avoid circular imports
from .routes import *


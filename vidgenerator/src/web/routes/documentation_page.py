"""
Documentation Page Route
Dedicated page for viewing documentation, similar to debugger page
"""

from flask import Blueprint, render_template

documentation_page_bp = Blueprint('documentation_page', __name__)

@documentation_page_bp.route('/documentation', methods=['GET'])
@documentation_page_bp.route('/vidgenerator/documentation', methods=['GET'])
def documentation_page():
    """Render documentation page"""
    return render_template('documentation/index.html')


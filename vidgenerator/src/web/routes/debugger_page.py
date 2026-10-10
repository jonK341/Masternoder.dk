"""Route for debugger page"""
from flask import Blueprint, render_template

debugger_page_bp = Blueprint('debugger_page', __name__)

@debugger_page_bp.route('/debugger')
@debugger_page_bp.route('/vidgenerator/debugger')
def debugger_page():
    """Debugger page"""
    return render_template('debugger/index.html')


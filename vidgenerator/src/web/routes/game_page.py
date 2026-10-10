"""Route for game page"""
from flask import Blueprint, render_template

game_page_bp = Blueprint('game_page', __name__)

@game_page_bp.route('/game')
@game_page_bp.route('/vidgenerator/game')
def game_page():
    """Game page"""
    return render_template('game/index.html')


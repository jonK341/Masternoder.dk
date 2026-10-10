"""Monitor & Scanner routes"""
from flask import render_template

def register_monitor_scanner_routes(app):
    """Register monitor & scanner routes"""
    
    @app.route('/monitor-scanner', methods=['GET'], endpoint='monitor_scanner')
    @app.route('/vidgenerator/monitor-scanner', methods=['GET'], endpoint='monitor_scanner_vidgenerator')
    @app.route('/vidgenerator/monitor-scanner/', methods=['GET'], endpoint='monitor_scanner_vidgenerator_slash')
    def monitor_scanner_index():
        """Monitor & Scanner page"""
        return render_template('monitor_scanner.html')


"""
Landing Page Report and Debug System
Analyzes masternoder.dk landing page and provides improvements
"""
from flask import Blueprint, jsonify, request, render_template
import os
from pathlib import Path
from datetime import datetime
import json

landing_report_bp = Blueprint('landing_report', __name__)

class LandingPageAnalyzer:
    """Analyze and improve landing page"""
    
    def __init__(self):
        self.base_path = Path('/var/www/html/vidgenerator')
        self.template_path = self.base_path / 'src/web/templates'
    
    def analyze_landing_page(self) -> dict:
        """Comprehensive landing page analysis"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'template_exists': False,
            'structure': {},
            'links': {},
            'issues': [],
            'recommendations': [],
            'improvements': []
        }
        
        # Check template file
        home_template = self.template_path / 'home.html'
        analysis['template_exists'] = home_template.exists()
        
        if home_template.exists():
            # Read and analyze template
            with open(home_template, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for generator link
            has_generator_link = '/vidgenerator/generator' in content or '/generator' in content
            analysis['links']['generator'] = has_generator_link
            
            # Check for other important links
            analysis['links']['gallery'] = '/gallery' in content or '/vidgenerator/gallery' in content
            analysis['links']['game'] = '/game' in content or '/vidgenerator/game' in content
            analysis['links']['debugger'] = '/debugger' in content or '/vidgenerator/debugger' in content
            analysis['links']['stats'] = '/stats' in content or '/vidgenerator/stats' in content
            
            # Check structure elements
            analysis['structure']['has_header'] = '<header' in content or '<h1' in content
            analysis['structure']['has_navigation'] = '<nav' in content or 'navigation' in content.lower()
            analysis['structure']['has_footer'] = '<footer' in content
            analysis['structure']['has_css'] = '<style' in content or '.css' in content
            analysis['structure']['has_js'] = '<script' in content or '.js' in content
            
            # Check for issues
            if not has_generator_link:
                analysis['issues'].append('Missing generator link')
                analysis['recommendations'].append('Add prominent link to video generator')
            
            if not analysis['structure']['has_navigation']:
                analysis['issues'].append('Missing navigation structure')
                analysis['recommendations'].append('Add navigation menu')
            
            if not analysis['structure']['has_footer']:
                analysis['issues'].append('Missing footer')
                analysis['recommendations'].append('Add footer with links and info')
        
        else:
            analysis['issues'].append('Home template file not found')
            analysis['recommendations'].append('Create home.html template')
        
        # Generate improvements
        analysis['improvements'] = self._generate_improvements(analysis)
        
        return analysis
    
    def _generate_improvements(self, analysis: dict) -> list:
        """Generate improvement suggestions"""
        improvements = []
        
        if not analysis['links'].get('generator'):
            improvements.append({
                'type': 'link',
                'priority': 'high',
                'action': 'Add prominent generator link',
                'description': 'Add a clear call-to-action link to the video generator'
            })
        
        if not analysis['structure'].get('has_navigation'):
            improvements.append({
                'type': 'structure',
                'priority': 'high',
                'action': 'Add navigation menu',
                'description': 'Create a navigation menu with links to all major sections'
            })
        
        improvements.append({
            'type': 'logic',
            'priority': 'medium',
            'action': 'Add dynamic content',
            'description': 'Add dynamic stats, recent videos, or featured content'
        })
        
        improvements.append({
            'type': 'logic',
            'priority': 'medium',
            'action': 'Add user engagement',
            'description': 'Add interactive elements, animations, or gamification'
        })
        
        improvements.append({
            'type': 'structure',
            'priority': 'low',
            'action': 'Add footer',
            'description': 'Add footer with links, copyright, and additional navigation'
        })
        
        return improvements

analyzer = LandingPageAnalyzer()

@landing_report_bp.route('/api/landing/report', methods=['GET'])
def get_landing_report():
    """Get landing page analysis report"""
    try:
        report = analyzer.analyze_landing_page()
        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@landing_report_bp.route('/api/landing/track-action', methods=['POST'])
def track_landing_action():
    """Track user actions on landing page"""
    try:
        data = request.get_json()
        action = data.get('action', 'unknown')
        timestamp = data.get('timestamp', datetime.now().isoformat())
        
        # Log action (could be stored in database)
        print(f"[Landing] Action tracked: {action} at {timestamp}")
        
        return jsonify({
            'success': True,
            'message': 'Action tracked',
            'action': action
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@landing_report_bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for platform verification"""
    try:
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'platform': 'MasterNoder.dk'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'error',
            'error': str(e)
        }), 500

@landing_report_bp.route('/landing-report')
@landing_report_bp.route('/vidgenerator/landing-report')
def landing_report_page():
    """Landing page report viewer"""
    return render_template('landing_report.html')


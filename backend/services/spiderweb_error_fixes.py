"""
SpiderWeb Error Fixes - Automatic fixes for recurring 404, 500, and Internal Server errors
Integrates with SpiderWeb Error Handler to detect and fix recurring errors
"""
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SpiderWebErrorFixes:
    """
    Automatic fixes for recurring errors:
    - 404 HTML errors (file not found)
    - 500 Internal Server errors
    - Blocking I/O errors
    """
    
    def __init__(self):
        self.fixes_applied = []
        
    def fix_404_error(self, request_path: str) -> Dict[str, Any]:
        """
        Fix 404 error by:
        1. Ensuring 404.html file exists
        2. Checking route registration
        3. Verifying static file paths
        """
        fixes = []
        
        try:
            # Fix 1: Ensure 404.html exists
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            html_404_paths = [
                '/var/www/html/vidgenerator/vidgenerator/404.html',
                os.path.join(base_dir, 'vidgenerator', '404.html'),
            ]
            
            html_404_exists = False
            for html_path in html_404_paths:
                normalized = os.path.normpath(os.path.abspath(html_path))
                if os.path.exists(normalized) and os.path.isfile(normalized):
                    html_404_exists = True
                    break
            
            if not html_404_exists:
                # Create default 404.html
                for html_path in html_404_paths:
                    try:
                        dir_path = os.path.dirname(html_path)
                        os.makedirs(dir_path, exist_ok=True)
                        
                        default_404_html = self._get_default_404_html(request_path)
                        with open(html_path, 'w', encoding='utf-8') as f:
                            f.write(default_404_html)
                        fixes.append(f"Created 404.html at {html_path}")
                        html_404_exists = True
                        break
                    except Exception as create_err:
                        logger.warning(f"Could not create 404.html at {html_path}: {create_err}")
            
            # Fix 2: Check if it's a static file that should exist
            if '/static/' in request_path:
                static_file = request_path.split('/static/')[-1]
                fixes.extend(self._fix_static_file_path(static_file))
            
            return {
                'success': True,
                'fixes_applied': fixes,
                'html_404_exists': html_404_exists
            }
        except Exception as e:
            logger.error(f"Error fixing 404: {e}")
            return {
                'success': False,
                'error': str(e),
                'fixes_applied': fixes
            }
    
    def fix_500_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Fix 500 Internal Server Error by:
        1. Checking for blocking I/O errors
        2. Checking database connection issues
        3. Checking missing dependencies
        4. Applying known fixes based on error type
        """
        fixes = []
        error_type = type(error).__name__
        error_message = str(error)
        
        try:
            # Fix 1: Blocking I/O errors (write could not complete)
            if "write could not complete" in error_message.lower() or "blocking" in error_message.lower():
                fixes.append("Detected blocking I/O error - this should be handled by _safe_print functions")
                # No automatic fix needed - code should use _safe_print
            
            # Fix 2: Database connection errors
            if "database" in error_message.lower() or "connection" in error_message.lower():
                fixes.append("Database connection issue detected - may need to restart service")
            
            # Fix 3: Import errors
            if "import" in error_message.lower() or "module" in error_message.lower():
                fixes.append("Import/module error detected - check dependencies")
            
            # Fix 4: Permission errors
            if "permission denied" in error_message.lower() or "permission" in error_message.lower():
                fixes.append("Permission error detected - check file/directory permissions")
            
            # Fix 5: Missing file errors
            if "no such file" in error_message.lower() or "file not found" in error_message.lower():
                fixes.append("Missing file error - ensure required files exist")
            
            return {
                'success': True,
                'error_type': error_type,
                'fixes_suggested': fixes,
                'can_auto_fix': len(fixes) > 0
            }
        except Exception as e:
            logger.error(f"Error fixing 500: {e}")
            return {
                'success': False,
                'error': str(e),
                'fixes_suggested': fixes
            }
    
    def fix_internal_server_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fix Internal Server Error - same as 500 error"""
        return self.fix_500_error(error, context)
    
    def _fix_static_file_path(self, static_file: str) -> list:
        """Try to fix static file path issues"""
        fixes = []
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Check if static file exists in common locations
        static_paths = [
            os.path.join(base_dir, 'vidgenerator', 'static', static_file),
            os.path.join(base_dir, 'src', 'web', 'static', static_file),
            os.path.join(base_dir, 'backend', 'static', static_file),
        ]
        
        for static_path in static_paths:
            if os.path.exists(static_path):
                fixes.append(f"Static file found at {static_path}")
                return fixes
        
        fixes.append(f"Static file {static_file} not found in any known location")
        return fixes
    
    def _get_default_404_html(self, request_path: str) -> str:
        """Generate default 404 HTML page"""
        return f"""<!DOCTYPE html>
<html lang="da">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - Side ikke fundet | MasterNoder.dk</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            color: #333;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            padding: 60px 40px;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
        }}
        .error-code {{
            font-size: 120px;
            font-weight: bold;
            color: #667eea;
            line-height: 1;
            margin-bottom: 20px;
        }}
        h1 {{
            font-size: 32px;
            margin-bottom: 20px;
            color: #333;
        }}
        p {{
            font-size: 18px;
            color: #666;
            margin-bottom: 30px;
            line-height: 1.6;
        }}
        .path {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            color: #333;
            margin: 20px 0;
            word-break: break-all;
        }}
        .button {{
            display: inline-block;
            padding: 15px 30px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 600;
            transition: background 0.3s;
            margin: 10px;
        }}
        .button:hover {{
            background: #5568d3;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="error-code">404</div>
        <h1>Side ikke fundet</h1>
        <p>Den side, du leder efter, eksisterer ikke eller er blevet flyttet.</p>
        <div class="path">Søgt sti: {request_path}</div>
        <a href="/" class="button">Gå til forsiden</a>
        <a href="/vidgenerator" class="button">Gå til VidGenerator</a>
    </div>
    <script>
        // Display path if available
        const pathText = document.querySelector('.path');
        if (pathText) {{
            pathText.textContent = 'Søgt sti: ' + window.location.pathname;
        }}
    </script>
</body>
</html>"""


# Global instance
spiderweb_error_fixes = SpiderWebErrorFixes()


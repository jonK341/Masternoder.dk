"""
Comprehensive Vidgenerator Audit System
Finds all missing components, routes, disabled features, and integration points
"""
import os
import re
from typing import Dict, List, Set, Tuple
from pathlib import Path

class VidgeneratorAuditor:
    """Comprehensive auditor for vidgenerator structure"""
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vidgenerator')
        self.findings = {
            'missing_routes': [],
            'missing_links': [],
            'disabled_features': [],
            'missing_integrations': [],
            'broken_references': [],
            'pages_without_nav': []
        }
    
    def audit_all(self) -> Dict:
        """Run complete audit"""
        print("Starting comprehensive vidgenerator audit...")
        
        # Find all pages
        pages = self._find_all_pages()
        print(f"Found {len(pages)} pages")
        
        # Check routes
        self._audit_routes(pages)
        
        # Check links
        self._audit_links(pages)
        
        # Check disabled features
        self._audit_disabled_features()
        
        # Check integrations
        self._audit_integrations(pages)
        
        # Check broken references
        self._audit_broken_references(pages)
        
        return self.findings
    
    def _find_all_pages(self) -> List[Dict]:
        """Find all HTML pages in vidgenerator"""
        pages = []
        vidgenerator_path = Path(self.base_path)
        
        if not vidgenerator_path.exists():
            return pages
        
        for html_file in vidgenerator_path.rglob('index.html'):
            rel_path = html_file.relative_to(vidgenerator_path)
            page_dir = rel_path.parent
            page_name = str(page_dir) if str(page_dir) != '.' else 'index'
            
            pages.append({
                'name': page_name,
                'path': str(html_file),
                'url': f'/vidgenerator/{page_name}/' if page_name != 'index' else '/vidgenerator/',
                'dir': str(page_dir)
            })
        
        return pages
    
    def _audit_routes(self, pages: List[Dict]):
        """Check if all pages have routes"""
        route_file = os.path.join(os.path.dirname(self.base_path), 'backend', 'routes', 'all_page_routes.py')
        
        if not os.path.exists(route_file):
            self.findings['missing_routes'] = [p['name'] for p in pages]
            return
        
        with open(route_file, 'r', encoding='utf-8') as f:
            route_content = f.read()
        
        for page in pages:
            page_name = page['name']
            if page_name == 'index':
                continue
            
            # Check if route exists
            route_pattern = f"@all_page_routes_bp.route.*['\"]/{page_name}"
            if not re.search(route_pattern, route_content):
                self.findings['missing_routes'].append(page_name)
    
    def _audit_links(self, pages: List[Dict]):
        """Check navigation links in all pages"""
        page_names = {p['name'] for p in pages}
        
        for page in pages:
            try:
                with open(page['path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find all internal links
                links = re.findall(r'href=["\'](/vidgenerator/[^"\']+)["\']', content)
                
                for link in links:
                    # Extract page name from link
                    link_parts = link.strip('/').split('/')
                    if len(link_parts) >= 2:
                        linked_page = link_parts[1]
                        if linked_page not in page_names and linked_page not in ['api', 'static']:
                            self.findings['missing_links'].append({
                                'from': page['name'],
                                'to': linked_page,
                                'link': link
                            })
            except Exception as e:
                print(f"Error auditing links in {page['path']}: {e}")
    
    def _audit_disabled_features(self):
        """Find disabled/commented features"""
        vidgenerator_path = Path(self.base_path)
        
        for html_file in vidgenerator_path.rglob('*.html'):
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find commented out features
                commented_blocks = re.findall(r'<!--.*?(disabled|TODO|FIXME|not.*?implemented|coming.*?soon).*?-->', content, re.IGNORECASE | re.DOTALL)
                
                # Find disabled JavaScript
                disabled_js = re.findall(r'//\s*(disabled|TODO|FIXME|not.*?implemented).*', content, re.IGNORECASE)
                
                if commented_blocks or disabled_js:
                    self.findings['disabled_features'].append({
                        'file': str(html_file.relative_to(self.base_path)),
                        'commented': len(commented_blocks),
                        'disabled_js': len(disabled_js)
                    })
            except Exception as e:
                print(f"Error checking disabled features in {html_file}: {e}")
    
    def _audit_integrations(self, pages: List[Dict]):
        """Check for missing API integrations"""
        required_apis = [
            'unified-point-counters',
            'progression-triggers',
            'quick-battle-frontend',
            'all-api-integration'
        ]
        
        for page in pages:
            try:
                with open(page['path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                missing = []
                for api in required_apis:
                    if api not in content:
                        missing.append(api)
                
                if missing:
                    self.findings['missing_integrations'].append({
                        'page': page['name'],
                        'missing_apis': missing
                    })
            except Exception as e:
                print(f"Error checking integrations in {page['path']}: {e}")
    
    def _audit_broken_references(self, pages: List[Dict]):
        """Check for broken static file references"""
        static_path = Path(self.base_path) / 'static'
        
        for page in pages:
            try:
                with open(page['path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find static file references
                static_refs = re.findall(r'["\'](/vidgenerator/static/[^"\']+)["\']', content)
                
                for ref in static_refs:
                    # Remove query strings
                    ref_path = ref.split('?')[0]
                    # Convert to file path
                    file_path = static_path / ref_path.replace('/vidgenerator/static/', '')
                    
                    if not file_path.exists():
                        self.findings['broken_references'].append({
                            'page': page['name'],
                            'reference': ref,
                            'expected_path': str(file_path)
                        })
            except Exception as e:
                print(f"Error checking references in {page['path']}: {e}")


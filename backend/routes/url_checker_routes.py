"""
URL Checker Routes
Provides endpoints for checking broken URLs and missing links
"""
from flask import Blueprint, jsonify, request, current_app
import os
import re
import requests
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Set
from collections import defaultdict
import concurrent.futures

url_checker_bp = Blueprint('url_checker', __name__)

# Navigation links from navigation-toolbar.js
NAV_LINKS = [
    "/vidgenerator/",
    "/vidgenerator/dashboard",
    "/vidgenerator/aggregator",
    "/vidgenerator/generator",
    "/vidgenerator/gallery",
    "/vidgenerator/game",
    "/vidgenerator/battle",
    "/vidgenerator/battlegrounds",
    "/vidgenerator/champions-league",
    "/vidgenerator/stats",
    "/vidgenerator/profile",
    "/vidgenerator/social",
    "/vidgenerator/shop",
    "/vidgenerator/chat",
    "/vidgenerator/metal",
    "/vidgenerator/theme-points",
    "/vidgenerator/victory-tech-tree",
    "/vidgenerator/danish-divine-tech-tree",
    "/vidgenerator/debugger",
    "/vidgenerator/analytics",
]

# Common API endpoints to check
API_ENDPOINTS = [
    "/vidgenerator/api/ai-video/generate",
    "/vidgenerator/api/ai-clips/generate",
    "/vidgenerator/api/generator/create",
    "/vidgenerator/api/generator/ai-clips",
    "/vidgenerator/api/debug/routes/list",
    "/vidgenerator/api/debug/errors/scan",
    "/vidgenerator/api/system/fix-all",
    "/vidgenerator/api/system/fix-log",
]

def check_url(url: str, base_url: str = None) -> Dict:
    """Check if a URL is accessible"""
    if base_url is None:
        base_url = request.host_url.rstrip('/')
        # Use https for production-like checking
        if 'localhost' not in base_url and '127.0.0.1' not in base_url:
            base_url = base_url.replace('http://', 'https://')
    
    full_url = urljoin(base_url, url)
    
    try:
        response = requests.head(full_url, timeout=10, allow_redirects=True)
        return {
            "url": url,
            "status": response.status_code,
            "success": 200 <= response.status_code < 400,
            "content_type": response.headers.get('content-type', ''),
            "error": None
        }
    except requests.exceptions.Timeout:
        return {
            "url": url,
            "status": 0,
            "success": False,
            "error": "Timeout"
        }
    except requests.exceptions.ConnectionError:
        return {
            "url": url,
            "status": 0,
            "success": False,
            "error": "Connection Error"
        }
    except Exception as e:
        return {
            "url": url,
            "status": 0,
            "success": False,
            "error": str(e)[:100]
        }

def find_urls_in_content(content: str, file_path: str = "") -> Set[str]:
    """Find URLs in content"""
    urls = set()
    
    # Regex patterns to find URLs
    patterns = [
        r'href=["\']([^"\']+)["\']',
        r'src=["\']([^"\']+)["\']',
        r'url\(["\']?([^"\'()]+)["\']?\)',
        r'fetch\(["\']([^"\']+)["\']',
        r'["\']([/]vidgenerator[^"\']+)["\']',
        r'["\']([/]api[^"\']+)["\']',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            # Skip external URLs, data URIs, and fragments
            if match.startswith(('http://', 'https://', 'data:', 'mailto:', 'tel:', '#', 'javascript:')):
                continue
            
            # Normalize URL
            url = match.strip()
            if url and (url.startswith('/') or url.startswith('./') or url.startswith('../')):
                # Convert relative to absolute
                if url.startswith('./'):
                    url = url[2:]
                elif url.startswith('../'):
                    url = url.replace('../', '')
                if not url.startswith('/'):
                    url = '/' + url
                urls.add(url)
    
    return urls

@url_checker_bp.route('/api/url-checker/check-navigation', methods=['GET'])
@url_checker_bp.route('/vidgenerator/api/url-checker/check-navigation', methods=['GET'])
def check_navigation_links():
    """Check all navigation links"""
    try:
        base_url = request.args.get('base_url')
        if not base_url:
            base_url = request.host_url.rstrip('/')
        
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(check_url, url, base_url): url for url in NAV_LINKS}
            for future in concurrent.futures.as_completed(future_to_url):
                result = future.result()
                results[result["url"]] = result
        
        working = [url for url, r in results.items() if r["success"]]
        broken = [{"url": url, "status": r["status"], "error": r.get("error")} 
                  for url, r in results.items() if not r["success"]]
        
        return jsonify({
            "success": True,
            "summary": {
                "total": len(NAV_LINKS),
                "working": len(working),
                "broken": len(broken)
            },
            "working": working,
            "broken": broken,
            "all_results": results
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@url_checker_bp.route('/api/url-checker/check-api', methods=['GET'])
@url_checker_bp.route('/vidgenerator/api/url-checker/check-api', methods=['GET'])
def check_api_endpoints():
    """Check all API endpoints"""
    try:
        base_url = request.args.get('base_url')
        if not base_url:
            base_url = request.host_url.rstrip('/')
        
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(check_url, url, base_url): url for url in API_ENDPOINTS}
            for future in concurrent.futures.as_completed(future_to_url):
                result = future.result()
                results[result["url"]] = result
        
        working = [url for url, r in results.items() if r["success"]]
        broken = [{"url": url, "status": r["status"], "error": r.get("error")} 
                  for url, r in results.items() if not r["success"]]
        
        return jsonify({
            "success": True,
            "summary": {
                "total": len(API_ENDPOINTS),
                "working": len(working),
                "broken": len(broken)
            },
            "working": working,
            "broken": broken,
            "all_results": results
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@url_checker_bp.route('/api/url-checker/check-url', methods=['POST'])
@url_checker_bp.route('/vidgenerator/api/url-checker/check-url', methods=['POST'])
def check_single_url():
    """Check a single URL"""
    try:
        data = request.get_json() or {}
        url = data.get('url')
        base_url = data.get('base_url')
        
        if not url:
            return jsonify({
                "success": False,
                "error": "URL is required"
            }), 400
        
        if not base_url:
            base_url = request.host_url.rstrip('/')
        
        result = check_url(url, base_url)
        
        return jsonify({
            "success": True,
            "result": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@url_checker_bp.route('/api/url-checker/check-all', methods=['GET'])
@url_checker_bp.route('/vidgenerator/api/url-checker/check-all', methods=['GET'])
def check_all_urls():
    """Check all navigation links and API endpoints"""
    try:
        base_url = request.args.get('base_url')
        if not base_url:
            base_url = request.host_url.rstrip('/')
        
        all_urls = NAV_LINKS + API_ENDPOINTS
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(check_url, url, base_url): url for url in all_urls}
            for future in concurrent.futures.as_completed(future_to_url):
                result = future.result()
                results[result["url"]] = result
        
        working = [url for url, r in results.items() if r["success"]]
        broken = [{"url": url, "status": r["status"], "error": r.get("error")} 
                  for url, r in results.items() if not r["success"]]
        missing = [{"url": url, "status": r["status"], "error": r.get("error")} 
                   for url, r in results.items() if r["status"] == 404]
        
        return jsonify({
            "success": True,
            "summary": {
                "total": len(all_urls),
                "working": len(working),
                "broken": len(broken),
                "missing": len(missing)
            },
            "working": working,
            "broken": broken,
            "missing": missing,
            "all_results": results
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@url_checker_bp.route('/api/url-checker/scan-files', methods=['POST'])
@url_checker_bp.route('/vidgenerator/api/url-checker/scan-files', methods=['POST'])
def scan_files_for_urls():
    """Scan files for URLs (limited to safe directories)"""
    try:
        data = request.get_json() or {}
        file_paths = data.get('file_paths', [])
        
        # Limit to safe directories
        safe_dirs = ['vidgenerator', 'backend']
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        found_urls = set()
        file_url_map = {}
        
        for file_path in file_paths:
            # Security check
            abs_path = os.path.abspath(file_path)
            if not any(abs_path.startswith(os.path.join(base_path, d)) for d in safe_dirs):
                continue
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    urls = find_urls_in_content(content, file_path)
                    found_urls.update(urls)
                    file_url_map[file_path] = list(urls)
                except Exception as e:
                    continue
        
        return jsonify({
            "success": True,
            "total_urls": len(found_urls),
            "urls": list(found_urls),
            "files": file_url_map
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


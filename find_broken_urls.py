#!/usr/bin/env python3
"""
Find Broken URLs and Missing Links
Scans the codebase for all URLs and checks if they're broken or missing
"""
import os
import re
import sys
import json
import requests
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Set, Tuple
from collections import defaultdict
import concurrent.futures

# Configure stdout for Unicode
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "https://masternoder.dk"
TIMEOUT = 10
MAX_WORKERS = 10

# Directories to scan
SCAN_DIRECTORIES = [
    "vidgenerator",
    "backend",
]

# File extensions to scan
SCAN_EXTENSIONS = [".html", ".js", ".py", ".css", ".json"]

# Regex patterns to find URLs
URL_PATTERNS = [
    r'href=["\']([^"\']+)["\']',  # href="..."
    r'src=["\']([^"\']+)["\']',   # src="..."
    r'url\(["\']?([^"\'()]+)["\']?\)',  # url(...)
    r'["\']([/][^"\']+)["\']',    # "/path"
    r'fetch\(["\']([^"\']+)["\']',  # fetch("...")
    r'["\']([/]vidgenerator[^"\']+)["\']',  # "/vidgenerator/..."
    r'["\']([/]api[^"\']+)["\']',  # "/api/..."
]

def find_all_urls_in_file(file_path: str) -> Set[str]:
    """Find all URLs in a file"""
    urls = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            for pattern in URL_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Skip external URLs, data URIs, and fragments
                    if match.startswith('http://') or match.startswith('https://'):
                        continue
                    if match.startswith('data:') or match.startswith('mailto:') or match.startswith('tel:'):
                        continue
                    if match.startswith('#'):
                        continue
                    if match.startswith('javascript:'):
                        continue
                    
                    # Normalize URL
                    url = match.strip()
                    if url and (url.startswith('/') or url.startswith('./') or url.startswith('../')):
                        urls.add(url)
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
    
    return urls

def scan_directory(directory: str) -> Dict[str, Set[str]]:
    """Scan a directory for URLs"""
    file_urls = defaultdict(set)
    
    for root, dirs, files in os.walk(directory):
        # Skip hidden directories and node_modules
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]
        
        for file in files:
            if any(file.endswith(ext) for ext in SCAN_EXTENSIONS):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path)
                urls = find_all_urls_in_file(file_path)
                if urls:
                    file_urls[rel_path] = urls
    
    return file_urls

def normalize_url(url: str, base_path: str = "") -> str:
    """Normalize a URL"""
    # Remove query strings and fragments for checking
    url = url.split('?')[0].split('#')[0]
    
    # Handle relative paths
    if url.startswith('./'):
        url = url[2:]
    elif url.startswith('../'):
        # For simplicity, just remove ../
        url = url.replace('../', '')
    
    # Ensure absolute path
    if not url.startswith('/'):
        url = '/' + url
    
    # Ensure vidgenerator prefix for internal URLs
    if url.startswith('/') and not url.startswith('/vidgenerator') and not url.startswith('/api') and not url.startswith('/static'):
        # Try to determine if this should be under /vidgenerator
        if any(keyword in url for keyword in ['dashboard', 'battle', 'stats', 'social', 'shop', 'chat', 'metal', 'theme-points', 'debugger', 'analytics', 'generator', 'gallery', 'game', 'profile', 'victory-tech-tree', 'danish-divine-tech-tree']):
            url = '/vidgenerator' + url
    
    return url

def check_url(url: str) -> Dict:
    """Check if a URL is accessible"""
    full_url = urljoin(BASE_URL, url)
    
    try:
        response = requests.head(full_url, timeout=TIMEOUT, allow_redirects=True)
        
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

def check_urls(urls: Set[str]) -> Dict[str, Dict]:
    """Check multiple URLs in parallel"""
    results = {}
    
    # Normalize and deduplicate URLs
    normalized_urls = set()
    for url in urls:
        normalized = normalize_url(url)
        if normalized:
            normalized_urls.add(normalized)
    
    # Check URLs in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(check_url, url): url for url in normalized_urls}
        
        for future in concurrent.futures.as_completed(future_to_url):
            result = future.result()
            results[result["url"]] = result
    
    return results

def main():
    print("=" * 80)
    print("FINDING BROKEN URLS AND MISSING LINKS")
    print("=" * 80)
    print()
    
    # Step 1: Scan directories for URLs
    print("[1/3] Scanning codebase for URLs...")
    all_file_urls = {}
    for directory in SCAN_DIRECTORIES:
        if os.path.exists(directory):
            print(f"  Scanning {directory}/...")
            file_urls = scan_directory(directory)
            all_file_urls.update(file_urls)
    
    # Collect all unique URLs
    all_urls = set()
    for urls in all_file_urls.values():
        all_urls.update(urls)
    
    print(f"  Found {len(all_urls)} unique URLs in {len(all_file_urls)} files")
    print()
    
    # Step 2: Check URLs
    print("[2/3] Checking URLs...")
    url_results = check_urls(all_urls)
    
    # Categorize results
    working_urls = []
    broken_urls = []
    missing_urls = []
    
    for url, result in url_results.items():
        if result["success"]:
            working_urls.append(url)
        elif result["status"] == 404:
            missing_urls.append(url)
        else:
            broken_urls.append((url, result))
    
    print(f"  Working: {len(working_urls)}")
    print(f"  Missing (404): {len(missing_urls)}")
    print(f"  Broken (other): {len(broken_urls)}")
    print()
    
    # Step 3: Generate report
    print("[3/3] Generating report...")
    
    report = {
        "summary": {
            "total_urls": len(all_urls),
            "working": len(working_urls),
            "missing": len(missing_urls),
            "broken": len(broken_urls),
            "files_scanned": len(all_file_urls)
        },
        "missing_urls": sorted(missing_urls),
        "broken_urls": [{"url": url, "status": r["status"], "error": r.get("error")} for url, r in broken_urls],
        "working_urls": sorted(working_urls),
        "urls_by_file": {}
    }
    
    # Map URLs back to files
    url_to_files = defaultdict(list)
    for file_path, urls in all_file_urls.items():
        for url in urls:
            normalized = normalize_url(url)
            if normalized in url_results:
                url_to_files[normalized].append(file_path)
    
    report["urls_by_file"] = {
        file: list(set([normalize_url(u) for u in urls])) 
        for file, urls in all_file_urls.items()
    }
    
    # Save report
    report_file = "broken_urls_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total URLs found: {report['summary']['total_urls']}")
    print(f"Working URLs: {report['summary']['working']}")
    print(f"Missing URLs (404): {report['summary']['missing']}")
    print(f"Broken URLs: {report['summary']['broken']}")
    print(f"Report saved to: {report_file}")
    print()
    
    # Print missing URLs
    if missing_urls:
        print("MISSING URLS (404):")
        print("-" * 80)
        for url in sorted(missing_urls)[:20]:  # Show first 20
            files = url_to_files.get(url, [])
            print(f"  {url}")
            for file in files[:3]:  # Show first 3 files
                print(f"    → {file}")
        if len(missing_urls) > 20:
            print(f"  ... and {len(missing_urls) - 20} more")
        print()
    
    # Print broken URLs
    if broken_urls:
        print("BROKEN URLS:")
        print("-" * 80)
        for url, result in broken_urls[:20]:  # Show first 20
            files = url_to_files.get(url, [])
            status = result["status"]
            error = result.get("error", "")
            print(f"  {url} [HTTP {status}] {error}")
            for file in files[:3]:  # Show first 3 files
                print(f"    → {file}")
        if len(broken_urls) > 20:
            print(f"  ... and {len(broken_urls) - 20} more")
        print()
    
    print("=" * 80)

if __name__ == "__main__":
    main()


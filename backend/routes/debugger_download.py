"""
Debugger Download API
Provides downloadable debugger tools and scripts
"""

from flask import Blueprint, send_file, jsonify, request, Response
import os
import zipfile
import tempfile
from pathlib import Path

debugger_download_bp = Blueprint('debugger_download', __name__)

# Available debugger tools
DEBUGGER_TOOLS = {
    'python': {
        'name': 'Python Debugger Script',
        'description': 'Standalone Python script for debugging the video generator',
        'filename': 'vidgenerator_debugger.py',
        'type': 'python',
        'mimetype': 'text/x-python'
    },
    'bash': {
        'name': 'Bash Debugger Script',
        'description': 'Bash script for system diagnostics and fixes',
        'filename': 'vidgenerator_debugger.sh',
        'type': 'bash',
        'mimetype': 'text/x-sh'
    },
    'powershell': {
        'name': 'PowerShell Debugger Script',
        'description': 'PowerShell script for Windows debugging',
        'filename': 'vidgenerator_debugger.ps1',
        'type': 'powershell',
        'mimetype': 'text/x-powershell'
    },
    'batch': {
        'name': 'Windows Batch Debugger',
        'description': 'Windows batch file for quick diagnostics',
        'filename': 'vidgenerator_debugger.bat',
        'type': 'batch',
        'mimetype': 'text/plain'
    },
    'full_package': {
        'name': 'Complete Debugger Package',
        'description': 'All debugger tools in one ZIP file',
        'filename': 'vidgenerator_debugger_package.zip',
        'type': 'zip',
        'mimetype': 'application/zip'
    }
}

def generate_python_debugger():
    """Generate Python debugger script"""
    return '''#!/usr/bin/env python3
"""
Video Generator Debugger Tool
Standalone Python script for debugging masternoder.dk/vidgenerator
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "https://masternoder.dk/vidgenerator"

def print_header(text):
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)

def test_endpoint(endpoint, method="GET", data=None):
    """Test an API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        return {
            'status': response.status_code,
            'success': response.status_code == 200,
            'data': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:500]
        }
    except Exception as e:
        return {
            'status': 0,
            'success': False,
            'error': str(e)
        }

def main():
    print_header("Video Generator Debugger Tool")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test system info
    print("Testing System Info...")
    result = test_endpoint("/api/debug/system-info")
    if result['success']:
        print("✓ System info accessible")
        print(json.dumps(result['data'], indent=2))
    else:
        print(f"✗ System info failed: {result.get('error', 'Unknown error')}")
    print()
    
    # Test logs
    print("Testing Logs...")
    result = test_endpoint("/api/debug/logs")
    if result['success']:
        print("✓ Logs accessible")
        logs = result['data'].get('logs', [])
        print(f"Found {len(logs)} log entries")
    else:
        print(f"✗ Logs failed: {result.get('error', 'Unknown error')}")
    print()
    
    # Test routes
    print("Testing Routes...")
    result = test_endpoint("/api/debug/routes/list")
    if result['success']:
        print("✓ Routes accessible")
        routes = result['data'].get('routes', [])
        print(f"Found {len(routes)} routes")
    else:
        print(f"✗ Routes failed: {result.get('error', 'Unknown error')}")
    print()
    
    # Test error scan
    print("Scanning for Errors...")
    result = test_endpoint("/api/debug/errors/scan")
    if result['success']:
        print("✓ Error scan complete")
        errors = result['data'].get('errors', [])
        print(f"Found {len(errors)} errors")
        for error in errors[:5]:  # Show first 5
            print(f"  - {error.get('type', 'Unknown')}: {error.get('message', 'No message')[:50]}")
    else:
        print(f"✗ Error scan failed: {result.get('error', 'Unknown error')}")
    print()
    
    print_header("Debug Complete")
    print("For more information, visit: https://masternoder.dk/vidgenerator/debugger")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\\n\\nDebugger interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\n\\nError: {e}")
        sys.exit(1)
'''

def generate_bash_debugger():
    """Generate Bash debugger script"""
    return '''#!/bin/bash
# Video Generator Debugger Tool
# Bash script for system diagnostics

BASE_URL="https://masternoder.dk/vidgenerator"

echo "============================================================"
echo "  Video Generator Debugger Tool"
echo "============================================================"
echo "Target: $BASE_URL"
echo "Time: $(date)"
echo ""

echo "Testing System Info..."
response=$(curl -s -w "\\n%{http_code}" "$BASE_URL/api/debug/system-info")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo "✓ System info accessible"
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
else
    echo "✗ System info failed (HTTP $http_code)"
fi
echo ""

echo "Testing Logs..."
response=$(curl -s -w "\\n%{http_code}" "$BASE_URL/api/debug/logs")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo "✓ Logs accessible"
    log_count=$(echo "$body" | jq '.logs | length' 2>/dev/null || echo "0")
    echo "Found $log_count log entries"
else
    echo "✗ Logs failed (HTTP $http_code)"
fi
echo ""

echo "Testing Routes..."
response=$(curl -s -w "\\n%{http_code}" "$BASE_URL/api/debug/routes/list")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo "✓ Routes accessible"
    route_count=$(echo "$body" | jq '.routes | length' 2>/dev/null || echo "0")
    echo "Found $route_count routes"
else
    echo "✗ Routes failed (HTTP $http_code)"
fi
echo ""

echo "============================================================"
echo "Debug Complete"
echo "For more information, visit: https://masternoder.dk/vidgenerator/debugger"
echo "============================================================"
'''

def generate_powershell_debugger():
    """Generate PowerShell debugger script"""
    return '''# Video Generator Debugger Tool
# PowerShell script for Windows debugging

$BaseUrl = "https://masternoder.dk/vidgenerator"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Video Generator Debugger Tool" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Target: $BaseUrl"
Write-Host "Time: $(Get-Date)"
Write-Host ""

Write-Host "Testing System Info..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/debug/system-info" -Method Get -TimeoutSec 10
    Write-Host "✓ System info accessible" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 3
} catch {
    Write-Host "✗ System info failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

Write-Host "Testing Logs..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/debug/logs" -Method Get -TimeoutSec 10
    Write-Host "✓ Logs accessible" -ForegroundColor Green
    $logCount = ($response.logs | Measure-Object).Count
    Write-Host "Found $logCount log entries"
} catch {
    Write-Host "✗ Logs failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

Write-Host "Testing Routes..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/debug/routes/list" -Method Get -TimeoutSec 10
    Write-Host "✓ Routes accessible" -ForegroundColor Green
    $routeCount = ($response.routes | Measure-Object).Count
    Write-Host "Found $routeCount routes"
} catch {
    Write-Host "✗ Routes failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Debug Complete" -ForegroundColor Cyan
Write-Host "For more information, visit: https://masternoder.dk/vidgenerator/debugger" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
'''

def generate_batch_debugger():
    """Generate Windows batch debugger script"""
    return '''@echo off
REM Video Generator Debugger Tool
REM Windows batch file for quick diagnostics

set BASE_URL=https://masternoder.dk/vidgenerator

echo ============================================================
echo   Video Generator Debugger Tool
echo ============================================================
echo Target: %BASE_URL%
echo Time: %date% %time%
echo.

echo Testing System Info...
curl -s "%BASE_URL%/api/debug/system-info" > temp_response.json 2>nul
if %errorlevel% equ 0 (
    echo [OK] System info accessible
    type temp_response.json
) else (
    echo [ERROR] System info failed
)
echo.

echo Testing Logs...
curl -s "%BASE_URL%/api/debug/logs" > temp_logs.json 2>nul
if %errorlevel% equ 0 (
    echo [OK] Logs accessible
) else (
    echo [ERROR] Logs failed
)
echo.

echo Testing Routes...
curl -s "%BASE_URL%/api/debug/routes/list" > temp_routes.json 2>nul
if %errorlevel% equ 0 (
    echo [OK] Routes accessible
) else (
    echo [ERROR] Routes failed
)
echo.

del temp_*.json 2>nul

echo ============================================================
echo Debug Complete
echo For more information, visit: https://masternoder.dk/vidgenerator/debugger
echo ============================================================
pause
'''

@debugger_download_bp.route('/download/<tool_type>')
@debugger_download_bp.route('/api/debugger/download/<tool_type>')
@debugger_download_bp.route('/api/fixer/download/<tool_type>')
@debugger_download_bp.route('/download/fixer/<tool_type>')
@debugger_download_bp.route('/vidgenerator/download/fixer/<tool_type>')
@debugger_download_bp.route('/tools/<tool_type>')
@debugger_download_bp.route('/vidgenerator/tools/<tool_type>')
def download_debugger(tool_type):
    """Download debugger tool - Multiple paths for resistance"""
    if tool_type not in DEBUGGER_TOOLS:
        return jsonify({
            'error': 'Invalid tool type',
            'available_tools': list(DEBUGGER_TOOLS.keys())
        }), 400
    
    tool_info = DEBUGGER_TOOLS[tool_type]
    
    if tool_type == 'full_package':
        # Create ZIP with all tools
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, tool_info['filename'])
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add Python script
                zipf.writestr('vidgenerator_debugger.py', generate_python_debugger())
                # Add Bash script
                zipf.writestr('vidgenerator_debugger.sh', generate_bash_debugger())
                # Add PowerShell script
                zipf.writestr('vidgenerator_debugger.ps1', generate_powershell_debugger())
                # Add Batch script
                zipf.writestr('vidgenerator_debugger.bat', generate_batch_debugger())
                # Add README
                readme = f"""# Video Generator Debugger Tools

This package contains debugger tools for masternoder.dk/vidgenerator

## Files:
- vidgenerator_debugger.py - Python script (cross-platform)
- vidgenerator_debugger.sh - Bash script (Linux/Mac)
- vidgenerator_debugger.ps1 - PowerShell script (Windows)
- vidgenerator_debugger.bat - Batch script (Windows)

## Usage:
- Python: python vidgenerator_debugger.py
- Bash: bash vidgenerator_debugger.sh
- PowerShell: .\\vidgenerator_debugger.ps1
- Batch: vidgenerator_debugger.bat

## Requirements:
- Python: requests library (pip install requests)
- Bash: curl, jq (optional)
- PowerShell: Built-in (Windows)
- Batch: curl (Windows 10+)

For more information, visit: https://masternoder.dk/vidgenerator/debugger
"""
                zipf.writestr('README.txt', readme)
            
            # Read ZIP file content
            with open(zip_path, 'rb') as f:
                zip_content = f.read()
            
            # Create response with proper headers
            response = Response(
                zip_content,
                mimetype='application/zip',
                headers={
                    'Content-Disposition': f'attachment; filename="{tool_info["filename"]}"',
                    'Content-Type': 'application/zip',
                    'Content-Length': str(len(zip_content)),
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
            
            # Clean up temp directory
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            
            return response
            
        except Exception as e:
            # Clean up on error
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            return jsonify({'error': f'Failed to create package: {str(e)}'}), 500
    
    else:
        # Generate single tool
        if tool_type == 'python':
            content = generate_python_debugger()
            mimetype = tool_info['mimetype']
        elif tool_type == 'bash':
            content = generate_bash_debugger()
            mimetype = tool_info['mimetype']
        elif tool_type == 'powershell':
            content = generate_powershell_debugger()
            mimetype = tool_info['mimetype']
        elif tool_type == 'batch':
            content = generate_batch_debugger()
            mimetype = tool_info['mimetype']
        else:
            return jsonify({'error': 'Unknown tool type'}), 400
        
        # Encode content to bytes
        content_bytes = content.encode('utf-8')
        
        # Create response with proper headers
        response = Response(
            content_bytes,
            mimetype=mimetype,
            headers={
                'Content-Disposition': f'attachment; filename="{tool_info["filename"]}"',
                'Content-Type': f'{mimetype}; charset=utf-8',
                'Content-Length': str(len(content_bytes)),
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
        
        return response

@debugger_download_bp.route('/api/debugger/tools')
@debugger_download_bp.route('/api/fixer/tools')
def list_debugger_tools():
    """List available debugger tools - Multiple paths for resistance"""
    base_url = request.host_url.rstrip('/')
    
    # Generate multiple download paths for each tool
    tools_with_paths = {}
    for tool_id, tool_info in DEBUGGER_TOOLS.items():
        tools_with_paths[tool_id] = {
            **tool_info,
            'download_paths': [
                f"{base_url}/api/debugger/download/{tool_id}",
                f"{base_url}/api/debugger/download/{tool_id}",
                f"{base_url}/vidgenerator/download/fixer/{tool_id}",
                f"{base_url}/download/fixer/{tool_id}",
                f"{base_url}/vidgenerator/tools/{tool_id}",
                f"{base_url}/tools/{tool_id}"
            ]
        }
    
    return jsonify({
        'tools': tools_with_paths,
        'base_url': base_url,
        'resistant_paths': True,
        'message': 'Multiple download paths available for resistance'
    })

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Error Logging API
Tests if the error logging API endpoints are working
"""
import requests
import json

BASE_URL = "https://masternoder.dk/vidgenerator/api/errors"

def test_error_logging_api():
    """Test error logging API endpoints"""
    print("=" * 70)
    print("TESTING ERROR LOGGING API")
    print("=" * 70)
    print()
    
    # Test 1: Stats endpoint
    print("Test 1: GET /stats")
    try:
        response = requests.get(f"{BASE_URL}/stats?days=1", timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  [OK] Stats endpoint working")
            print(f"  Total errors: {data.get('total_errors', 'N/A')}")
        else:
            print(f"  [ERROR] Unexpected status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  [ERROR] {e}")
    print()
    
    # Test 2: List endpoint
    print("Test 2: GET /list")
    try:
        response = requests.get(f"{BASE_URL}/list?limit=5", timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  [OK] List endpoint working")
            print(f"  Total errors: {data.get('total', 'N/A')}")
        else:
            print(f"  [ERROR] Unexpected status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  [ERROR] {e}")
    print()
    
    # Test 3: Log endpoint
    print("Test 3: POST /log")
    try:
        test_error = {
            "error_type": "javascript",
            "error_level": "info",
            "error_message": "Test error from verification script",
            "page_url": "/vidgenerator/debugger"
        }
        response = requests.post(f"{BASE_URL}/log", json=test_error, timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 201:
            data = response.json()
            print(f"  [OK] Log endpoint working")
            print(f"  Error ID: {data.get('error_id', 'N/A')}")
        else:
            print(f"  [ERROR] Unexpected status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  [ERROR] {e}")
    print()
    
    # Test 4: Handler status endpoint
    print("Test 4: GET /handler-status/analyze")
    try:
        response = requests.get(f"{BASE_URL}/handler-status/analyze", timeout=30)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  [OK] Handler status endpoint working")
            if data.get('success') and data.get('analysis'):
                analysis = data['analysis']
                print(f"  Total files: {analysis.get('total_files', 'N/A')}")
                print(f"  Files with ErrorManager: {analysis.get('files_with_error_manager', 'N/A')}")
        else:
            print(f"  [ERROR] Unexpected status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  [ERROR] {e}")
    print()
    
    print("=" * 70)
    print("TESTING COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    test_error_logging_api()

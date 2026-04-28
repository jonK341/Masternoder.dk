#!/usr/bin/env python3
"""Test generator endpoints directly to see what's happening."""
import requests
import sys

BASE_URL = "https://masternoder.dk"
endpoints = [
    "/vidgenerator/api/generator/test",
    "/vidgenerator/api/generator/jobs",
    "/vidgenerator/api/generator/history",
    "/vidgenerator/api/generator/statistics",
    "/vidgenerator/api/generator/performance",
]

print("Testing generator endpoints:")
print("=" * 70)
for endpoint in endpoints:
    url = BASE_URL + endpoint
    try:
        r = requests.get(url, timeout=10)
        print(f"{endpoint:50} -> {r.status_code} ({len(r.content)} bytes)")
        if r.status_code == 200:
            try:
                data = r.json()
                print(f"  Response keys: {list(data.keys())[:5]}")
            except:
                print(f"  Response: {r.text[:100]}")
        elif r.status_code == 404:
            print(f"  404 - Route not found")
    except Exception as e:
        print(f"{endpoint:50} -> ERROR: {e}")

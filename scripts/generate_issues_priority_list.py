#!/usr/bin/env python3
"""
Generate Issues Priority List
Creates a prioritized action list from system overview
"""
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def generate_priority_list():
    """Generate prioritized action list"""
    print("=" * 70)
    print("ISSUES PRIORITY LIST")
    print("=" * 70)
    print()
    
    # Read overview report
    report_file = os.path.join(BASE_DIR, 'system_overview_report.json')
    if os.path.exists(report_file):
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
    else:
        print("  [WARN] Overview report not found, using defaults")
        report = {
            'issues': {
                '404 Errors': ['131/200 requests returned 404'],
                'Console Errors': ['1 unique console errors found']
            },
            'warnings': {
                'User Management': ['default_user is still being used'],
                'Hardcoded Values': ['backend-connector.js contains default_user']
            }
        }
    
    # Priority categories
    priorities = {
        'CRITICAL': [],
        'HIGH': [],
        'MEDIUM': [],
        'LOW': []
    }
    
    # Categorize issues
    if 'Missing Endpoints' in report.get('issues', {}):
        priorities['CRITICAL'].extend([
            "Fix missing API endpoints returning 404",
            "Implement placeholder endpoints with real logic"
        ])
    
    if '404 Errors' in report.get('issues', {}):
        priorities['CRITICAL'].append("Fix 404 errors - 131/200 requests failing")
    
    if 'User Management' in report.get('warnings', {}):
        priorities['HIGH'].extend([
            "Integrate user identification system fully",
            "Replace all default_user fallbacks",
            "Auto-create users on first visit"
        ])
    
    if 'Console Errors' in report.get('issues', {}):
        priorities['HIGH'].append("Fix JavaScript console errors")
    
    if 'Server Errors' in report.get('issues', {}):
        priorities['CRITICAL'].append("Fix server errors (500+)")
    
    # Add standard items
    priorities['MEDIUM'].extend([
        "Implement placeholder endpoints (12 endpoints)",
        "Add comprehensive error logging",
        "Standardize database schema",
        "Add API response caching",
        "Implement rate limiting"
    ])
    
    priorities['LOW'].extend([
        "Review TODO/FIXME comments (6 found)",
        "Optimize performance",
        "Add monitoring/alerting",
        "Improve documentation"
    ])
    
    # Print priority list
    for priority, items in priorities.items():
        if items:
            print(f"[{priority}] ({len(items)} items)")
            for i, item in enumerate(items, 1):
                print(f"  {i}. {item}")
            print()
    
    # Save to file
    output_file = os.path.join(BASE_DIR, 'ISSUES_PRIORITY_LIST.md')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Issues Priority List\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for priority, items in priorities.items():
            if items:
                f.write(f"## {priority} Priority\n\n")
                for i, item in enumerate(items, 1):
                    f.write(f"{i}. {item}\n")
                f.write("\n")
    
    print(f"Priority list saved to: {output_file}")
    print()
    print("=" * 70)
    print("PRIORITY LIST COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    generate_priority_list()

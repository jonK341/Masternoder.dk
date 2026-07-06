#!/usr/bin/env python3
"""
UI Audit Script - Finds holes and inconsistencies in frontend UI
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Set
from bs4 import BeautifulSoup


class UIAuditor:
    """Audits UI for holes and inconsistencies"""
    
    def __init__(self):
        self.issues: List[Dict] = []
        self.html_files: List[Path] = []
        
    def find_html_files(self, root_dir: str = ".") -> List[Path]:
        """Find all HTML files"""
        html_files = []
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'server_backup', 'vidgenerator.backup']]
            for file in files:
                if file.endswith('.html'):
                    html_files.append(Path(root) / file)
        return html_files
    
    def check_missing_alt_text(self, html_file: Path) -> List[Dict]:
        """Check for images without alt text"""
        issues = []
        try:
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            images = soup.find_all('img')
            
            for img in images:
                if not img.get('alt'):
                    issues.append({
                        'type': 'missing_alt',
                        'file': str(html_file),
                        'element': str(img)[:100],
                        'severity': 'medium'
                    })
        except Exception as e:
            issues.append({
                'type': 'parse_error',
                'file': str(html_file),
                'error': str(e),
                'severity': 'low'
            })
        
        return issues
    
    def check_broken_internal_links(self, html_file: Path) -> List[Dict]:
        """Check for potentially broken internal links"""
        issues = []
        try:
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '').strip()
                
                # Check for common issues
                if href.startswith('/'):
                    # Check for double slashes
                    if '//' in href[1:]:
                        issues.append({
                            'type': 'double_slash',
                            'file': str(html_file),
                            'href': href,
                            'severity': 'low'
                        })
                    
                    # Check for missing trailing slash where needed
                    if href.endswith('/') and len(href) > 1:
                        # Some routes might need trailing slash
                        pass
                
                # Check for relative paths that might be wrong
                if not href.startswith('/') and not href.startswith('http') and '..' in href:
                    issues.append({
                        'type': 'relative_path',
                        'file': str(html_file),
                        'href': href,
                        'severity': 'medium'
                    })
        except Exception as e:
            pass
        
        return issues
    
    def check_missing_meta_tags(self, html_file: Path) -> List[Dict]:
        """Check for missing important meta tags"""
        issues = []
        try:
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Check for viewport meta tag
            viewport = soup.find('meta', attrs={'name': 'viewport'})
            if not viewport:
                issues.append({
                    'type': 'missing_viewport',
                    'file': str(html_file),
                    'severity': 'high'
                })
            
            # Check for charset
            charset = soup.find('meta', attrs={'charset': True})
            if not charset:
                issues.append({
                    'type': 'missing_charset',
                    'file': str(html_file),
                    'severity': 'high'
                })
        except Exception:
            pass
        
        return issues
    
    def check_inconsistent_styling(self, html_file: Path) -> List[Dict]:
        """Check for inconsistent styling patterns"""
        issues = []
        try:
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Check for inline styles (should use CSS classes)
            inline_style_count = len(re.findall(r'style\s*=', content, re.IGNORECASE))
            if inline_style_count > 10:
                issues.append({
                    'type': 'too_many_inline_styles',
                    'file': str(html_file),
                    'count': inline_style_count,
                    'severity': 'low'
                })
            
            # Check for mixed quote styles
            single_quotes = content.count("'")
            double_quotes = content.count('"')
            if abs(single_quotes - double_quotes) > 100:
                issues.append({
                    'type': 'inconsistent_quotes',
                    'file': str(html_file),
                    'severity': 'low'
                })
        except Exception:
            pass
        
        return issues
    
    def check_accessibility(self, html_file: Path) -> List[Dict]:
        """Check for accessibility issues"""
        issues = []
        try:
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Check for buttons without aria-labels
            buttons = soup.find_all('button')
            for button in buttons:
                if not button.get('aria-label') and not button.get_text(strip=True):
                    issues.append({
                        'type': 'button_no_label',
                        'file': str(html_file),
                        'severity': 'medium'
                    })
            
            # Check for form inputs without labels
            inputs = soup.find_all(['input', 'textarea', 'select'])
            for inp in inputs:
                inp_id = inp.get('id')
                if inp_id:
                    label = soup.find('label', attrs={'for': inp_id})
                    if not label:
                        # Check if label wraps input
                        parent_label = inp.find_parent('label')
                        if not parent_label:
                            issues.append({
                                'type': 'input_no_label',
                                'file': str(html_file),
                                'input_type': inp.name,
                                'severity': 'medium'
                            })
        except Exception:
            pass
        
        return issues
    
    def audit_all(self):
        """Run all audits"""
        print("🔍 Starting UI audit...")
        
        self.html_files = self.find_html_files()
        print(f"Found {len(self.html_files)} HTML files to audit\n")
        
        for html_file in self.html_files:
            print(f"Auditing: {html_file}")
            
            # Run all checks
            self.issues.extend(self.check_missing_alt_text(html_file))
            self.issues.extend(self.check_broken_internal_links(html_file))
            self.issues.extend(self.check_missing_meta_tags(html_file))
            self.issues.extend(self.check_inconsistent_styling(html_file))
            self.issues.extend(self.check_accessibility(html_file))
        
        print(f"\n✅ Audit complete. Found {len(self.issues)} issues")
    
    def generate_report(self) -> str:
        """Generate audit report"""
        report = []
        report.append("=" * 80)
        report.append("UI AUDIT REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Group by type
        by_type = {}
        by_severity = {'high': [], 'medium': [], 'low': []}
        
        for issue in self.issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)
            
            severity = issue.get('severity', 'low')
            by_severity[severity].append(issue)
        
        report.append(f"📊 Summary:")
        report.append(f"  Total issues: {len(self.issues)}")
        report.append(f"  High severity: {len(by_severity['high'])}")
        report.append(f"  Medium severity: {len(by_severity['medium'])}")
        report.append(f"  Low severity: {len(by_severity['low'])}")
        report.append("")
        
        # High severity issues
        if by_severity['high']:
            report.append("🔴 HIGH SEVERITY ISSUES:")
            report.append("-" * 80)
            for issue in by_severity['high']:
                report.append(f"  Type: {issue['type']}")
                report.append(f"  File: {issue['file']}")
                if 'element' in issue:
                    report.append(f"  Element: {issue['element'][:60]}...")
                report.append("")
        
        # Medium severity issues
        if by_severity['medium']:
            report.append("🟡 MEDIUM SEVERITY ISSUES:")
            report.append("-" * 80)
            for issue in by_severity['medium'][:20]:  # Show first 20
                report.append(f"  {issue['type']} in {Path(issue['file']).name}")
            if len(by_severity['medium']) > 20:
                report.append(f"  ... and {len(by_severity['medium']) - 20} more")
            report.append("")
        
        # Issues by type
        report.append("📋 ISSUES BY TYPE:")
        report.append("-" * 80)
        for issue_type, issues_list in sorted(by_type.items()):
            report.append(f"  {issue_type}: {len(issues_list)}")
        
        return "\n".join(report)


def main():
    """Main function"""
    auditor = UIAuditor()
    auditor.audit_all()
    
    report = auditor.generate_report()
    print("\n" + report)
    
    # Save report
    with open('ui_audit_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n✅ Report saved to ui_audit_report.txt")
    
    if auditor.issues:
        print(f"\n⚠️  Found {len(auditor.issues)} UI issues to fix!")
    else:
        print("\n✅ No UI issues found!")


if __name__ == "__main__":
    main()


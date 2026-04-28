#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Debugger JavaScript Syntax Error
Finds and fixes the 'Unexpected token catch' error
"""
import re

def fix_syntax_error(file_path):
    """Fix JavaScript syntax errors in debugger HTML"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Find the Error Dashboard Scripts section
    script_start = content.find('<!-- Error Dashboard Scripts -->')
    if script_start == -1:
        print("Error Dashboard Scripts section not found")
        return False
    
    script_end = content.find('</script>', script_start + 2000)
    if script_end == -1:
        print("Script end not found")
        return False
    
    script_content = content[script_start:script_end+9]
    
    # Count braces
    open_braces = script_content.count('{')
    close_braces = script_content.count('}')
    print(f"Braces: {open_braces} open, {close_braces} close, diff: {open_braces - close_braces}")
    
    # Check for common syntax issues
    issues = []
    
    # Check for missing semicolons before catch
    if re.search(r'}\s*catch\s*\(', script_content):
        # This is fine
        pass
    
    # Check for unclosed function expressions
    if 'window.loadErrorStats = async function()' in script_content:
        # Check if it's properly closed
        func_start = script_content.find('window.loadErrorStats = async function()')
        func_body = script_content[func_start:]
        # Count braces from function start
        func_open = func_body[:func_body.rfind('};')].count('{')
        func_close = func_body[:func_body.rfind('};')].count('}')
        if func_open != func_close:
            issues.append(f"loadErrorStats: {func_open} open, {func_close} close")
    
    print(f"Issues found: {len(issues)}")
    for issue in issues:
        print(f"  - {issue}")
    
    # The main issue is likely that functions aren't being defined because of the syntax error
    # Let me check if there's a missing closing brace in the IIFE or function definitions
    
    return len(issues) > 0

if __name__ == '__main__':
    fix_syntax_error('vidgenerator/debugger/index.html')

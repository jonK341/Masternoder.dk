#!/usr/bin/env python
"""
Test runner script for MasterNoder.dk test suite
Runs all tests with proper configuration
"""
import sys
import subprocess
from pathlib import Path

def run_tests(test_type='all', verbose=True, coverage=False):
    """
    Run tests with pytest
    
    Args:
        test_type: 'all', 'unit', 'integration', 'performance'
        verbose: Show verbose output
        coverage: Generate coverage report
    """
    project_root = Path(__file__).parent.parent
    test_dir = project_root / 'tests'
    
    # Build pytest command
    cmd = ['python', '-m', 'pytest']
    
    if test_type == 'all':
        cmd.append(str(test_dir))
    elif test_type in ['unit', 'integration', 'performance']:
        cmd.extend([f'tests/{test_type}/', '-m', test_type])
    else:
        print(f"Unknown test type: {test_type}")
        return False
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=backend', '--cov=src', '--cov-report=html', '--cov-report=term'])
    
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode == 0

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run MasterNoder.dk test suite')
    parser.add_argument('--type', choices=['all', 'unit', 'integration', 'performance'],
                       default='all', help='Type of tests to run')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Quiet mode (less verbose)')
    parser.add_argument('--coverage', '-c', action='store_true',
                       help='Generate coverage report')
    
    args = parser.parse_args()
    
    success = run_tests(
        test_type=args.type,
        verbose=not args.quiet,
        coverage=args.coverage
    )
    
    sys.exit(0 if success else 1)

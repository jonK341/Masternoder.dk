"""
Test runner script
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_tests():
    """Run all tests using pytest"""
    try:
        import pytest
    except ImportError:
        print("ERROR: pytest is not installed. Install it with: pip install pytest pytest-cov")
        sys.exit(1)
    
    # Run pytest with coverage
    test_dir = Path(__file__).parent
    exit_code = pytest.main([
        str(test_dir),
        '-v',  # Verbose
        '--tb=short',  # Short traceback format
        '--cov=src',  # Coverage for src directory
        '--cov-report=term-missing',  # Show missing lines in terminal
        '--cov-report=html',  # Generate HTML coverage report
    ])
    
    return exit_code


if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)


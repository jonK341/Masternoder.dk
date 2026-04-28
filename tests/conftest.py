"""
Pytest configuration and shared fixtures for MasterNoder.dk.
Ensures project root is on sys.path and cwd so backend/services and src can be imported.
Run from project root: pytest tests/ -v   or   pytest tests/unit/ -v
"""
import os
import sys
import pytest

# Project root (parent of tests/)
_ROOT = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(_ROOT) == "tests":
    _ROOT = os.path.dirname(_ROOT)

def pytest_configure(config):
    """Ensure project root is on path and cwd before any test runs."""
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    try:
        os.chdir(_ROOT)
    except OSError:
        pass


@pytest.fixture(scope="session")
def project_root():
    """Project root directory."""
    return _ROOT


@pytest.fixture(autouse=True)
def _ensure_cwd():
    """Each test runs with cwd = project root."""
    try:
        os.chdir(_ROOT)
    except OSError:
        pass

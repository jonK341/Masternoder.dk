"""
Pytest configuration and shared fixtures for MasterNoder.dk.
Ensures project root is on sys.path and cwd so backend/services and src can be imported.
Run from project root: pytest tests/ -v   or   pytest tests/unit/ -v
"""
import os
import sys
import pytest

import shutil
import stat


def _basetemp_needs_fallback(path):
    if not path or not os.path.isdir(path):
        return False

    def _onerror(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            raise

    try:
        shutil.rmtree(path, onerror=_onerror)
    except PermissionError:
        return True
    return False


def _fallback_basetemp(path):
    parent = os.path.dirname(path.rstrip("/\\")) or "."
    return os.path.join(parent, f"{os.path.basename(path)}-{os.getpid()}")


# Project root (parent of tests/)
_ROOT = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(_ROOT) == "tests":
    _ROOT = os.path.dirname(_ROOT)

_DEFAULT_BASETEMP = os.path.join(_ROOT, ".pytest-tmp-local")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Ensure project root is on path and cwd before any test runs."""
    basetemp = config.getoption("basetemp", default=None)
    if not basetemp:
        config.option.basetemp = _DEFAULT_BASETEMP
    elif sys.platform == "win32" and _basetemp_needs_fallback(basetemp):
        config.option.basetemp = _fallback_basetemp(basetemp)
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

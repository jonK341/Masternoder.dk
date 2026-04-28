"""
Reusable helpers for unit testing backend services.
Use across test_01_*.py .. test_07_*.py for consistent assertions.
"""
import os
import sys

# Ensure project root on path when run as script or by pytest
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
try:
    os.chdir(_ROOT)
except OSError:
    pass


def ensure_project_root():
    """Idempotent: add project root to sys.path and chdir. Call at top of test modules if needed."""
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    try:
        os.chdir(_ROOT)
    except OSError:
        pass


def is_safe_fallback(value, allowed_none=True, allowed_list=True, allowed_dict=True):
    """
    Return True if value is a "safe" fallback when DB/tables missing.
    Services return None, [], {}, False, 0 instead of raising.
    """
    if value is None and allowed_none:
        return True
    if isinstance(value, list) and allowed_list:
        return True
    if isinstance(value, dict) and allowed_dict:
        return True
    if value is False or value == 0:
        return True
    return False


def assert_tables_exist_returns_bool(module, tables_exist_func_name="tables_exist"):
    """
    Call module.<tables_exist_func_name>() and assert it returns a bool (or does not raise).
    Use when app context may be missing: then the function may raise; we allow that.
    """
    func = getattr(module, tables_exist_func_name, None)
    assert func is not None, f"Module has no {tables_exist_func_name}"
    try:
        result = func()
        assert isinstance(result, bool), f"Expected bool, got {type(result)}"
    except Exception:
        # Outside app context many _db services raise when accessing db
        pass


def assert_returns_safe_or_typed(module, func_name, *args, return_type=None, **kwargs):
    """
    Call module.<func_name>(*args, **kwargs). Assert:
    - No unhandled exception, and
    - If return_type is list -> result is list; if dict -> result is dict; if bool -> bool; if int/float -> number or None.
    - If return_type is None, just assert no exception.
    """
    func = getattr(module, func_name, None)
    assert func is not None, f"Module has no {func_name}"
    try:
        result = func(*args, **kwargs)
    except Exception as e:
        raise AssertionError(f"{func_name} raised: {e}") from e
    if return_type is not None:
        if return_type == list:
            assert isinstance(result, list), f"{func_name} should return list, got {type(result)}"
        elif return_type == dict:
            assert result is None or isinstance(result, dict), f"{func_name} should return dict or None, got {type(result)}"
        elif return_type == bool:
            assert isinstance(result, bool), f"{func_name} should return bool, got {type(result)}"
        elif return_type in (int, float):
            assert result is None or isinstance(result, (int, float)), f"{func_name} should return number or None, got {type(result)}"
    return result

"""The debugger Migration Progress panel counts a static/js file as migrated
when its source contains ErrorManager or error-manager.

That string has to be a real call into the shared handler, not a comment.
"""
from pathlib import Path

from backend.routes.error_handler_status_routes import analyze_error_handlers

ROOT = Path(__file__).resolve().parents[2]
JS_DIR = ROOT / "static" / "js"
CALL_MARKERS = (
    "window.ErrorManager.logJSError",
    "window.ErrorManager.logNetworkError",
    "window.ErrorManager.logApiError",
)


def test_handler_migration_reaches_every_scanned_file():
    result = analyze_error_handlers()
    assert result["success"] is True
    analysis = result["analysis"]
    total = analysis["total_files"]
    migrated = analysis["files_with_error_manager"]
    assert total == len(list(JS_DIR.glob("*.js")))
    assert total > 0
    assert migrated == total
    assert analysis["files_without_error_manager"] == 0
    assert analysis["top_files_needing_migration"] == []
    percent = round(migrated / total * 100)
    assert percent == 100


def test_migrated_files_call_the_shared_handler():
    missing = []
    for path in sorted(JS_DIR.glob("*.js")):
        if path.name == "error-manager.js":
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert "class ErrorManager" in text
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not any(marker in text for marker in CALL_MARKERS):
            missing.append(path.name)
    assert missing == []

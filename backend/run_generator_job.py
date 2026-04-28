"""
Run video generation in a separate process so uWSGI web workers stay free.
Usage: python -m backend.run_generator_job <doc_id>
Reads config from VIDEOS_DIR/<doc_id>.job.json (written by the create route).
Stderr is appended to VIDEOS_DIR/generator_subprocess.log for debugging.
"""
from __future__ import absolute_import
import os
import sys
import json
from datetime import datetime

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m backend.run_generator_job <doc_id>", file=sys.stderr)
        sys.exit(1)
    doc_id = sys.argv[1].strip()
    if not doc_id:
        sys.exit(2)

    # Ensure project root is on path (same as wsgi)
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    os.environ.setdefault("PYTHONPATH", _root + os.pathsep + os.environ.get("PYTHONPATH", ""))

    from backend.services.video_generator_service import (
        VIDEOS_DIR,
        _job_config_path,
        run_video_generation_standalone,
    )
    # Redirect stderr to a log file so "Config not found" and tracebacks are visible on server
    _stderr_log = os.path.join(VIDEOS_DIR, "generator_subprocess.log")
    try:
        _log = open(_stderr_log, "a", encoding="utf-8")
        _log.write("\n--- %s doc_id=%s ---\n" % (datetime.utcnow().isoformat(), doc_id))
        _log.flush()
        sys.stderr = _log
    except Exception:
        pass
    config_path = _job_config_path(doc_id)
    if not os.path.isfile(config_path):
        print("Config not found: %s" % config_path, file=sys.stderr)
        sys.stderr.flush()
        sys.exit(3)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print("Failed to load config: %s" % e, file=sys.stderr)
        if hasattr(sys.stderr, 'flush'):
            sys.stderr.flush()
        sys.exit(4)
    try:
        run_video_generation_standalone(doc_id, config)
    except Exception as e:
        print("Generation failed: %s" % e, file=sys.stderr)
        if hasattr(sys.stderr, 'flush'):
            sys.stderr.flush()
        try:
            from backend.services.video_generator_service import _write_status_sidecar
            _write_status_sidecar(
                doc_id=doc_id,
                status="failed",
                message="Generation failed",
                error_message=str(e),
                progress=0,
            )
        except Exception:
            pass
        sys.exit(5)
    # Optionally remove job config after success to avoid re-use
    try:
        if os.path.isfile(config_path):
            os.remove(config_path)
    except Exception:
        pass

if __name__ == "__main__":
    main()

"""Main entry point for the Automated Documentary Generator System"""
import os
import sys

# Get the directory containing this file (project root)
if "__file__" in globals():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
else:
    BASE_DIR = os.getcwd()

# Add project root to Python path FIRST (before any imports)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.environ["PYTHONPATH"] = BASE_DIR + os.pathsep + os.environ.get("PYTHONPATH", "")

try:
    os.chdir(BASE_DIR)
except Exception:
    pass

# Load environment variables before create_app so DATABASE_URL etc. are set
try:
    from dotenv import load_dotenv
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path) and os.access(env_path, os.R_OK):
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass
except Exception:
    pass

# Verify src directory exists before importing
_src_path = os.path.join(BASE_DIR, "src")
if not os.path.exists(_src_path):
    raise ImportError(
        f"src directory not found at {_src_path}. BASE_DIR={BASE_DIR}, sys.path={sys.path[:3]}"
    )

from src.app import create_app

app = create_app()
is_production = os.getenv("FLASK_ENV") == "production" or os.getenv("PRODUCTION") == "true"

if __name__ == "__main__":
    try:
        print("Initializing Documentary Generator...")
        output_dir = os.getenv("OUTPUT_DIR", "output")
        upload_dir = os.getenv("UPLOAD_DIR", "uploads")
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(os.path.join(upload_dir, "faces"), exist_ok=True)
        os.makedirs(os.path.join(upload_dir, "documents"), exist_ok=True)

        preferred_port = int(os.getenv("FLASK_PORT", "5000"))
        debug = not is_production and os.getenv("FLASK_DEBUG", "True").lower() == "true"

        import socket
        def port_free(p):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            free = s.connect_ex(("127.0.0.1", p)) != 0
            s.close()
            return free

        port = preferred_port if port_free(preferred_port) else 5003
        if not port_free(port):
            print(f"ERROR: Ports {preferred_port} and 5003 are both in use. Set FLASK_PORT in .env or free a port.")
            sys.exit(1)
        if port != preferred_port:
            print(f"Note: Port {preferred_port} in use, using port {port}")

        print("=" * 60)
        print("Documentary Generator")
        print(f"URL: http://127.0.0.1:{port}")
        print(f"Debug: {debug}")
        print("=" * 60)

        with app.test_client() as client:
            r = client.get("/api/health")
            print(f"[OK] Health: {r.status_code}")

        print("Press Ctrl+C to stop.")
        app.run(
            host="0.0.0.0",
            port=port,
            debug=debug,
            use_reloader=False,
            threaded=True,
            use_debugger=debug,
        )
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

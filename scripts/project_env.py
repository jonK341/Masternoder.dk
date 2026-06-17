"""Load /var/www/html/.env for CLI scripts (uWSGI loads it via systemd; CLI does not)."""
from __future__ import annotations

import os


def project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_project_dotenv() -> bool:
    """Load project .env into os.environ. Returns True if file was found."""
    path = os.path.join(project_root(), ".env")
    if not os.path.isfile(path):
        return False
    try:
        from dotenv import load_dotenv

        load_dotenv(path)
        return True
    except ImportError:
        # Minimal parser when python-dotenv is missing on server.
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
            return True
        except OSError:
            return False
    except Exception:
        return False


def rpc_env_status() -> dict:
    load_project_dotenv()
    return {
        "env_file": os.path.join(project_root(), ".env"),
        "env_loaded": os.path.isfile(os.path.join(project_root(), ".env")),
        "rpc_url": (os.environ.get("MN2_RPC_URL") or "").strip() or "http://127.0.0.1:9332",
        "rpc_user_set": bool((os.environ.get("MN2_RPC_USER") or "").strip()),
        "rpc_password_set": bool((os.environ.get("MN2_RPC_PASSWORD") or "").strip()),
    }


def probe_rpc() -> tuple[bool, str]:
    load_project_dotenv()
    try:
        from backend.services.mn2_rpc_client import getblockcount

        r = getblockcount()
        if isinstance(r, dict):
            if r.get("error"):
                return False, str(r.get("error"))
            height = r.get("result")
            if height is not None:
                return True, f"getblockcount OK (height={height})"
            return False, "getblockcount returned no result"
        return True, f"getblockcount OK (height={r})"
    except Exception as exc:
        return False, str(exc)
